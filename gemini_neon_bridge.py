import asyncio
import json
from typing import Any, Dict, List
from mcp import ClientSession
from mcp.client.sse import sse_client
import google.generativeai as genai

class GeminiNeonBridge:
    """Bridge between Google Gemini and Neon MCP Server"""
    
    def __init__(self, neon_api_key: str, gemini_api_key: str, project_id: str):
        self.neon_api_key = neon_api_key
        self.gemini_api_key = gemini_api_key
        self.project_id = project_id
        self.session: ClientSession | None = None
        self.sse_context = None
        self.tools: List[Dict[str, Any]] = []
        self.chat = None  # Persistent chat session
        self.model = None  # Persistent model instance
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)
    
    async def connect_to_neon(self):
        """Connect to Neon's managed MCP server"""
        url = "https://mcp.neon.tech/sse"
        headers = {
            "Authorization": f"Bearer {self.neon_api_key}"
        }
        
        self.sse_context = sse_client(url, headers=headers)
        streams = await self.sse_context.__aenter__()
        
        self.session = ClientSession(streams[0], streams[1])
        await self.session.__aenter__()
        await self.session.initialize()
        
        # Get available tools from Neon MCP
        tools_response = await self.session.list_tools()
        self.tools = self._convert_mcp_tools_to_gemini_format(tools_response.tools)
        
        print(f"✅ Connected to Neon MCP. Found {len(self.tools)} tools.")
        for tool in self.tools:
            print(f"   - {tool['name']}: {tool['description']}")
        
        return self.tools
    
    def _convert_mcp_tools_to_gemini_format(self, mcp_tools: List[Any]) -> List[Dict[str, Any]]:
        """Convert MCP tools to Gemini function calling format"""
        gemini_tools = []
        
        for tool in mcp_tools:
            # Convert MCP tool schema to Gemini function declaration format
            properties = {}
            required = []
            
            # Handle inputSchema - it might be a dict or an object with properties
            schema = None
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                schema = tool.inputSchema
            elif hasattr(tool, 'input_schema') and tool.input_schema:
                schema = tool.input_schema
            
            if schema:
                # If schema is a dict-like object, access it directly
                if isinstance(schema, dict):
                    schema_dict = schema
                else:
                    # Try to convert to dict
                    try:
                        schema_dict = dict(schema) if hasattr(schema, '__dict__') else {}
                    except:
                        schema_dict = {}
                
                if 'properties' in schema_dict:
                    for prop_name, prop_def in schema_dict['properties'].items():
                        prop_type = prop_def.get('type', 'string')
                        prop_schema = {
                            'type': prop_type,
                            'description': prop_def.get('description', '')
                        }
                        # Add enum if present
                        if 'enum' in prop_def:
                            prop_schema['enum'] = prop_def['enum']
                        # For array types, preserve items schema
                        if prop_type == 'array' and 'items' in prop_def:
                            prop_schema['items'] = prop_def['items']
                        properties[prop_name] = prop_schema
                
                if 'required' in schema_dict:
                    required = schema_dict['required']
            
            gemini_tool = {
                'name': tool.name,
                'description': tool.description or f"Tool: {tool.name}",
                'parameters': {
                    'type': 'object',
                    'properties': properties,
                    'required': required
                }
            }
            gemini_tools.append(gemini_tool)
        
        return gemini_tools
    
    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call on the Neon MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to Neon MCP. Call connect_to_neon() first.")
        
        # Ensure project_id is included in arguments if not present
        if 'projectId' not in arguments and 'project_id' not in arguments:
            arguments['projectId'] = self.project_id
        
        # Convert project_id to projectId if needed
        if 'project_id' in arguments:
            arguments['projectId'] = arguments.pop('project_id')
        
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _initialize_gemini_model(self, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize Gemini model and chat session (only once)"""
        if self.model is not None and self.chat is not None:
            return  # Already initialized
        
        # Convert tools to Gemini's function declaration format
        function_declarations = []
        for tool in self.tools:
            # Build properties dict for Gemini Schema
            properties = {}
            for prop_name, prop_def in tool['parameters']['properties'].items():
                prop_type_str = prop_def.get('type', 'string').lower()
                
                # Map to Gemini Type enum
                type_mapping = {
                    'string': genai.protos.Type.STRING,
                    'integer': genai.protos.Type.INTEGER,
                    'number': genai.protos.Type.NUMBER,
                    'boolean': genai.protos.Type.BOOLEAN,
                    'array': genai.protos.Type.ARRAY,
                    'object': genai.protos.Type.OBJECT,
                }
                gemini_type = type_mapping.get(prop_type_str, genai.protos.Type.STRING)
                
                # Build schema
                schema_kwargs = {
                    'type': gemini_type,
                    'description': prop_def.get('description', '')
                }
                
                # For array types, add items field (required by Gemini)
                if gemini_type == genai.protos.Type.ARRAY:
                    # Get items schema from prop_def
                    items_def = prop_def.get('items', {})
                    if isinstance(items_def, dict):
                        # Determine items type
                        items_type_str = items_def.get('type', 'string').lower()
                        items_type = type_mapping.get(items_type_str, genai.protos.Type.STRING)
                        schema_kwargs['items'] = genai.protos.Schema(
                            type=items_type,
                            description=items_def.get('description', '')
                        )
                    else:
                        # Default to string array if items not specified
                        schema_kwargs['items'] = genai.protos.Schema(
                            type=genai.protos.Type.STRING
                        )
                
                properties[prop_name] = genai.protos.Schema(**schema_kwargs)
            
            function_declarations.append(
                genai.protos.FunctionDeclaration(
                    name=tool['name'],
                    description=tool['description'],
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties=properties,
                        required=tool['parameters'].get('required', [])
                    )
                )
            )
        
        # Create tool config
        tool_config = genai.protos.Tool(
            function_declarations=function_declarations
        )
        
        # System instruction to guide Gemini's behavior
        system_instruction = f"""You are an autonomous database assistant with direct access to execute SQL queries on a Neon PostgreSQL database.

NEVER SAY that you need more information about the project or database or table to answer the question. Find that information yourself by executing SQL queries instead of asking user for more information.

CRITICAL BEHAVIOR RULES:
1. AUTOMATIC EXECUTION: When users ask about data, you MUST automatically generate SQL and execute it using the `run_sql` tool. Never just provide SQL code - always execute it.
2. PROJECT ID: Always include projectId="{self.project_id}" when calling `run_sql`.
3. PROACTIVE QUERIES: If asked "show me nodes for id 1" or similar, immediately execute: SELECT * FROM papi_automation WHERE id = 1
4. RESULT PRESENTATION: After executing queries, format and explain results clearly to the user.
5. SCHEMA EXPLORATION: Use `get_database_tables` or `describe_table_schema` if you need to understand the database structure first.

WORKFLOW EXAMPLES:

Example 1:
User: "What are the nodes in id 10?"
Your actions:
1. Call run_sql with: SELECT * FROM papi_automation WHERE id = 10
2. Present the results in a clear format
3. Explain what you found

Example 2:
User: "Show me the first 5 rows from papi_automation"
Your actions:
1. Call run_sql with: SELECT * FROM papi_automation LIMIT 5
2. Display the results in a table format
3. Summarize the data

NEVER:
- Say you don't have context and ask the user for project, database and table information
- Say "Here's the SQL query you can run" without executing it
- Ask users to run queries manually
- Provide SQL without executing it first

ALWAYS:
- If you don't have context, find it yourself by running the corresponding queries
- Execute queries automatically using run_sql
- Present results clearly
- Be helpful and proactive

journey_xray table in project-id late-brook-11506963 :
aid is Journey or Automation ID
channel is the channel of communication
cid is client id
glreqid is global request id
nid is node id
ts is timestamp
uid is user id

papi_automation table in project-id late-brook-11506963 :
id is journey or automation id
name is the journey name
lp_content_parsed contains the journey metadata
nodedatarray contains the information about the nodes in that journey
linkdatarray contains the information about the links between the nodes

id in papi_automation table is same as aid in journey_xray table

"""

        # Create model with tools and system instruction (persistent)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=[tool_config],
            system_instruction=system_instruction
        )
        
        # Start chat session (persistent - maintains history)
        self.chat = self.model.start_chat()
    
    async def chat_with_gemini(self, user_message: str, model_name: str = "gemini-2.0-flash-exp") -> str:
        """Chat with Gemini, allowing it to use Neon MCP tools with persistent memory"""
        if not self.session:
            await self.connect_to_neon()
        
        # Initialize model and chat if not already done
        if self.model is None or self.chat is None:
            self._initialize_gemini_model(model_name)
        
        # Send message to existing chat (maintains conversation history)
        response = self.chat.send_message(user_message)
        
        # Handle function calls in a loop
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check if there's a function call
            if not response.candidates:
                break
                
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content.parts:
                break
            
            # Check for function calls
            function_calls = []
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
            
            if not function_calls:
                break
            
            # Execute all function calls
            function_responses = []
            for function_call in function_calls:
                function_name = function_call.name
                # Convert args to dict
                function_args = {}
                if hasattr(function_call, 'args'):
                    if isinstance(function_call.args, dict):
                        function_args = function_call.args
                    else:
                        # Try to convert protobuf to dict
                        try:
                            function_args = dict(function_call.args)
                        except:
                            function_args = {}
                
                print(f"\n🔧 Gemini wants to call: {function_name}")
                print(f"   Arguments: {json.dumps(function_args, indent=2)}")
                
                # Execute the function
                function_result = await self.execute_tool_call(function_name, function_args)
                
                # Convert result to dict for Gemini
                if isinstance(function_result, dict):
                    result_dict = function_result
                else:
                    result_dict = {'result': str(function_result)}
                
                print(f"✅ Tool executed successfully")
                
                # Create function response
                function_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response=result_dict
                        )
                    )
                )
            
            # Send function responses back to Gemini (using persistent chat)
            response = self.chat.send_message(function_responses)
        
        # Extract text response
        if response.candidates and response.candidates[0].content.parts:
            text_parts = [
                part.text 
                for part in response.candidates[0].content.parts 
                if hasattr(part, 'text') and part.text
            ]
            return ' '.join(text_parts) if text_parts else str(response)
        
        return str(response)
    
    def reset_conversation(self):
        """Reset the conversation history (start a new chat)"""
        if self.model is not None:
            self.chat = self.model.start_chat()
            print("🔄 Conversation history reset")
    
    async def query_data(self, question: str, model_name: str = "gemini-2.0-flash-exp") -> str:
        """Query data with emphasis on automatic SQL execution"""
        # Add a prompt that emphasizes execution
        enhanced_prompt = f"""{question}

Remember: Execute the SQL query automatically using the run_sql tool. Do not just provide the SQL code - execute it and show the results."""
        
        return await self.chat_with_gemini(enhanced_prompt, model_name)
    
    async def disconnect(self):
        """Disconnect from Neon MCP"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
        if hasattr(self, 'sse_context') and self.sse_context:
            try:
                await self.sse_context.__aexit__(None, None, None)
            except Exception:
                pass
        # Reset chat and model
        self.chat = None
        self.model = None


async def main():
    """Example usage"""
    # Configuration - Replace with your actual keys
    NEON_API_KEY = "napi_hvi7pyuxz298lh9knvset2mbo6l6oc1hg1qpdd7qf6xg90mxr5lkco4zek3dy230"
    GEMINI_API_KEY = "AIzaSyAJhStqoy_zSxolzyUZXcFJJClkoNFILc8"  # Get from https://makersuite.google.com/app/apikey
    PROJECT_ID = "late-brook-11506963"
    
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("⚠️  Please set your GEMINI_API_KEY in the code!")
        print("   Get one from: https://makersuite.google.com/app/apikey")
        return
    
    bridge = GeminiNeonBridge(NEON_API_KEY, GEMINI_API_KEY, PROJECT_ID)
    
    try:
        # Connect to Neon
        await bridge.connect_to_neon()
        
        # Interactive chat loop
        print("\n" + "="*80)
        print("🤖 Gemini + Neon MCP Bridge")
        print("="*80)
        print("Type your questions about your Neon database.")
        print("Type 'exit' or 'quit' to end the conversation.")
        print("Type 'reset' to clear conversation history.\n")
        
        while True:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                bridge.reset_conversation()
                continue
            
            if not user_input:
                continue
            
            print("\n🤖 Gemini:")
            try:
                response = await bridge.chat_with_gemini(user_input)
                print(response)
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print("\n" + "-"*80 + "\n")
    
    finally:
        await bridge.disconnect()


if __name__ == "__main__":
    asyncio.run(main())


