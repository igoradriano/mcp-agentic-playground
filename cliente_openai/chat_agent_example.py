import asyncio
import os
from agents import Agent, ModelSettings, Runner, TResponseInputItem
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

async def chat_agent():
    # Carrega variáveis de ambiente (ex: API keys)
    load_dotenv()
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Inicia um servidor MCP via STDIO executando o server_sql.py
    async with MCPServerStdio(params={"command": "mcp", "args": ["run", "servers/server_sql.py"]}) as server:
        
        # Cria o agente de IA com acesso às tools do MCP
        agent = Agent(
            name="Assistant",
            model=model_name,
            instructions=("Você é um assistente de banco de dados. Utilize as ferramentas necessárias para acessar o schema ou consultar dados do banco."),
            mcp_servers=[server],  # Registra o servidor MCP
            model_settings=ModelSettings(tool_choice="auto", temperature=0)  # LLM decide quando usar tools.  Respostas determinísticas
        )

        print("Digite sair, exit ou quit para encerrar a conversa.")

        # Histórico da conversa (mensagens do usuário e do agente)
        history: list[TResponseInputItem] = []

        while True:
            message = input("Você: ") # Lê entrada do usuário
            if message.lower() in ["sair", "exit", "quit"]: # Condição de saída
                print("Encerrando a conversa.")
                break

            # Adiciona mensagem do usuário ao histórico
            history.append({
                "role": "user",
                "content": message
            })

            # Executa o agente com todo o histórico
            result = await Runner.run(
                starting_agent=agent,
                input=history
            )

            # Atualiza o histórico com mensagens geradas pelo agente
            history = result.to_input_list()

            # Exibe a resposta final do agente
            print(f"Assistente: {result.final_output}")


# Ponto de entrada do script
if __name__ == "__main__":
    asyncio.run(chat_agent())