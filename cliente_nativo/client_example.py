import asyncio
import os
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Ajuste do PYTHONPATH para permitir imports relativos ao diretório raiz
# -----------------------------------------------------------------------------
# Isso garante que o Python consiga localizar o módulo `classes.mcp_client`
# mesmo quando o script é executado diretamente.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from classes.mcp_client import McpClient # Import do cliente MCP responsável por comunicação com o servidor MCP

async def main():
    """
    Função principal assíncrona responsável por:
    - Inicializar o cliente MCP
    - Conectar ao servidor MCP (STDIO ou SSE)
    - Descobrir tools, resources e prompts
    - Executar exemplos de uso
    """
    # Instancia o cliente MCP
    client = McpClient()

    try:
        # ---------------------------------------------------------------------
        # Inicialização da conexão com o servidor MCP
        # ---------------------------------------------------------------------

        # Exemplo de conexão via STDIO (servidor local como processo)
        #await client.initialize_with_stdio("mcp", ["run", "servers/server_test.py"])
        
        # Inicialização via SSE (servidor MCP rodando como serviço HTTP)
        sse_url = os.getenv("MCP_SSE_URL", "http://localhost:8000/sse")
        await client.initialize_with_sse(sse_url)

        # ---------------------------------------------------------------------
        # Descoberta e uso de TOOLS
        # ---------------------------------------------------------------------
        print("Listando tools")
        tools = await client.get_tools()         # Solicita ao servidor MCP a lista de ferramentas disponíveis

        for tool in tools:
            print(f'Nome: {tool.name}, Descrição: {tool.description}') # Exibe nome e descrição de cada tool
            if tool.name == 'adiciona': # Caso exista uma tool específica chamada "adiciona"
                print("Chamando a ferramenta adiciona")

                result = await client.call_tool( # Executa a tool passando os argumentos esperados
                    "adiciona",
                    {"a": 1, "b": 200}
                )

                print(result.content[0].text)  # Exibe o resultado retornado pela ferramenta

        # ---------------------------------------------------------------------
        # Descoberta e uso de RESOURCES
        # ---------------------------------------------------------------------
        print("\nListando resources")
        resources = await client.get_resources() # Solicita ao servidor MCP a lista de recursos disponíveis

        for resource in resources:
            print(resource)  # Exibe metadados do resource

            if resource.mimeType == 'text/plain': # Verifica se o recurso é texto simples
                print(f"Acessando recurso {resource.name}")
                result = await client.get_resource(resource.uri) # Lê o conteúdo do resource usando sua URI
                print(result.contents[0].text) # Exibe o conteúdo retornado

        # ---------------------------------------------------------------------
        # Descoberta e uso de PROMPTS
        # ---------------------------------------------------------------------
        print("\nListando prompts")
        prompts = await client.get_prompts()  # Solicita ao servidor MCP a lista de prompts disponíveis

        for prompt in prompts:
            print(prompt) # Exibe informações do prompt

            if prompt.name == 'formatar_dado_cadastral': # Caso exista um prompt específico para formatação de CPF
                print("Formatando Dado Cadastral")

                result = await client.invoke_prompt( # Executa o prompt passando os argumentos necessários
                    prompt.name,
                    {"cpf": "12312312312"}
                )
                print(result.messages[0].content.text)  # Exibe o texto gerado pelo prompt

    finally:
        # ---------------------------------------------------------------------
        # Encerramento seguro das conexões MCP
        # ---------------------------------------------------------------------
        # Garante que todas as conexões e contextos assíncronos sejam fechados corretamente, mesmo em caso de erro
        await client.cleanup()


if __name__ == "__main__":
    # Executa a função principal dentro do event loop assíncrono
    asyncio.run(main())

