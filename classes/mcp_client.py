from mcp import ClientSession, Resource, StdioServerParameters, Tool
from mcp.types import Prompt, CallToolResult, ReadResourceResult, GetPromptResult
from mcp.client.stdio import stdio_client          # Cliente MCP via STDIO (processo local)
from mcp.client.sse import sse_client               # Cliente MCP via SSE (HTTP / remoto)
from contextlib import AsyncExitStack                # Gerencia múltiplos contextos async com segurança


class McpClient:
    """
    Cliente MCP responsável por:
    - Conectar-se a um servidor MCP (local ou remoto)
    - Descobrir tools, resources e prompts
    - Executar tools e ler resources
    - Servir como camada de integração entre LLMs e servidores MCP
    """

    def __init__(self):
        self.server_params: StdioServerParameters = None # Parâmetros do servidor MCP quando usado via STDIO
        self.session: ClientSession = None # Sessão MCP ativa (canal principal de comunicação com o servidor)
        self.exit_stack = AsyncExitStack() # Gerenciador de ciclo de vida de contextos assíncronos. Garante que conexões e recursos sejam fechados corretamente

    async def initialize_with_stdio(self, command: str, args: list):
        """
        Inicializa a conexão com um servidor MCP LOCAL utilizando STDIO.
        Esse modo é usado quando o servidor MCP:
        - roda como um processo local (ex: `python server.py`)
        - se comunica via stdin / stdout
        - NÃO expõe HTTP, API REST ou SSE

        Em termos simples:
        → este método "liga" o cliente MCP a um programa local
        e cria um canal de comunicação bidirecional com ele.
        """

        # Define COMO o processo do servidor MCP será iniciado
        # - command: executável (ex: "python")
        # - args: argumentos passados ao processo (ex: ["server.py"])
        self.server_params = StdioServerParameters(
            command=command,
            args=args,
        )

        # Inicia o processo do servidor MCP e abre o canal STDIO
        # O stdio_client: executa o processo, captura stdin (write) e stdout (read), retorna os streams de comunicação
        self.client = await self.exit_stack.enter_async_context(
            stdio_client(self.server_params)
        )

        # Separa os canais de comunicação:
        # - read  → tudo que o servidor MCP envia para o cliente
        # - write → tudo que o cliente envia para o servidor MCP
        read, write = self.client

        # Cria a sessão MCP propriamente dita
        # A ClientSession: implementa o protocolo MCP, gerencia mensagens, tools, resources e prompts, usa os streams read/write como transporte
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        # Executa o handshake inicial com o servidor MCP
        # Aqui acontece: validação do protocolo,  troca de capacidades, confirmação de que cliente e servidor falam MCP
        await self.session.initialize()


    async def initialize_with_sse(self, host: str):
        """
        Inicializa a conexão com um servidor MCP remoto via SSE (HTTP).
        Usado quando o servidor MCP está rodando como serviço web.
        """
        # Abre conexão SSE com o servidor MCP
        self.client = await self.exit_stack.enter_async_context(
            sse_client(host)
        )

        read, write = self.client

        # Cria a sessão MCP sobre o canal SSE
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        # Handshake inicial
        await self.session.initialize()

    async def get_tools(self) -> list[Tool]:
        """
        Lista todas as ferramentas (tools) expostas pelo servidor MCP.
        Tools representam ações executáveis (ex: SQL, APIs, cálculos).
        """
        response = await self.session.list_tools()
        return response.tools

    async def get_resources(self) -> list[Resource]:
        """
        Lista todos os resources disponíveis no servidor MCP.
        Resources representam dados persistentes ou consultáveis
        (ex: arquivos, tabelas, endpoints).
        """
        response = await self.session.list_resources()
        return response.resources

    async def get_prompts(self) -> list[Prompt]:
        """
        Lista prompts versionados e reutilizáveis
        definidos no servidor MCP.
        """
        response = await self.session.list_prompts()
        return response.prompts

    async def call_tool(self, tool_name: str, args: dict[str, object]) -> CallToolResult:
        """
        Executa uma tool específica no servidor MCP.
        :param tool_name: Nome da ferramenta
        :param args: Argumentos esperados pela tool
        """
        return await self.session.call_tool(
            tool_name,
            arguments=args
        )

    async def get_resource(self, uri: str) -> ReadResourceResult:
        """
        Lê um resource específico do servidor MCP
        a partir de sua URI.
        """
        return await self.session.read_resource(uri)

    async def invoke_prompt(self, prompt_name: str, args) -> GetPromptResult:
        """
        Executa um prompt MCP com argumentos dinâmicos.
        Prompts podem ser usados para padronizar instruções
        enviadas ao LLM.
        """
        return await self.session.get_prompt(
            prompt_name,
            arguments=args
        )

    def format_tools_llm(self, tools) -> list[object]:
        """
        Converte tools MCP para o formato esperado
        pela API de tool-calling de LLMs (ex: OpenAI).
        Isso permite que o modelo "enxergue" as tools
        e decida chamá-las automaticamente.
        """
        formatted_tools = []

        for tool in tools:
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
            })

        return formatted_tools

    async def cleanup(self) -> None:
        """
        Encerra corretamente todas as conexões e contextos abertos.
        Deve ser chamado no shutdown da aplicação
        para evitar vazamentos de recursos.
        """
        await self.exit_stack.aclose()