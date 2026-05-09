# Ajusta o sys.path para permitir importar módulos da pasta pai do projeto
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from dotenv import load_dotenv
import asyncio, json  # Importações auxiliares para execução assíncrona e manipulação de JSON

from classes.llm_client import LLmClient # Cliente responsável por interagir com o LLM
from classes.mcp_client import McpClient # Cliente responsável por interagir com o MCP (Model Context Protocol)

# Caminho do servidor MCP que expõe ferramentas SQL
tool = "servers/server_sql.py"

# Corrige bug de loop de eventos no Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Título centralizado da aplicação
st.markdown("<h1 style='text-align: center;'>NovoDive Motors</h1>", unsafe_allow_html=True)

# Cria layout em três colunas
left_co, cent_co, last_co = st.columns(3)
with cent_co:
    # Exibe a imagem central da aplicação
    st.image("arquivos/novadrive.png", caption="NovaDrive Motors")

# Inicializa o cliente LLM apenas uma vez na sessão
if "llmClient" not in st.session_state:
    load_dotenv()  # Carrega variáveis de ambiente (ex: chave da API)
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    st.session_state.llmClient = LLmClient(model_name)

# Função utilitária para executar corrotinas async em contexto síncrono
def run_task(coro):
    loop = asyncio.new_event_loop()             # Cria um novo event loop
    asyncio.set_event_loop(loop)                # Define o loop como atual
    task = loop.create_task(coro)               # Cria a task async
    return loop.run_until_complete(asyncio.wait_for(task, timeout=None)) 

# Inicializa as ferramentas MCP e armazena em session_state
if "tools" not in st.session_state:
    with st.spinner("Lendo ferramentas..."): 
        try:
            # Função assíncrona para inicializar o MCP e obter as tools
            async def init_mcp():
                client = McpClient() 
                await client.initialize_with_stdio("mcp", ["run", tool])   # Inicializa o MCP via stdio apontando para o servidor
                await asyncio.sleep(1)                                     # Pequena espera para estabilização
                tools = client.format_tools_llm(await client.get_tools())  # Obtém e formata as ferramentas para o LLM
                await client.cleanup()                                     # Finaliza a conexão
                return tools
            
            st.session_state.tools = run_task(init_mcp())                  # Executa a inicialização assíncrona
            st.success("Ferramentas lidas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao utilizar MCP Client: {str(e)}")             # Interrompe a aplicação caso haja erro ao carregar ferramentas
            st.stop()  

# Executa uma única chamada de ferramenta solicitada pelo LLM
def process_single_tool_call(call):
    try:
        # Função assíncrona que realiza a chamada da tool
        async def do_call():
            client = McpClient()  
            await client.initialize_with_stdio("mcp", ["run", tool])  

            # Executa a tool com os argumentos gerados pelo LLM
            tool_result = await client.call_tool(
                call.function.name,
                json.loads(call.function.arguments)
            )

            await client.cleanup()
            return tool_result

        # Executa a chamada assíncrona de forma síncrona
        call_result = run_task(do_call())

        # Concatena apenas os trechos textuais retornados pela tool
        return ''.join(item.text for item in call_result.content if item.type == 'text')
    except Exception as e:
        # Retorna mensagem de erro caso a tool falhe
        return f"Error calling tool: {str(e)}"  

# Processa a resposta do LLM, incluindo possíveis chamadas de tools
def resolve_chat(response):
    llm_client = st.session_state.llmClient
    tools = st.session_state.tools

    # Verifica se o LLM solicitou chamadas de ferramentas
    if response.choices[0].finish_reason == 'tool_calls':
        tool_reply = response.choices[0].message.content 

        # Exibe mensagem parcial do assistente (se houver)
        if tool_reply is not None:
            with st.chat_message("assistant"):
                st.markdown(tool_reply)

        # Extrai as chamadas de ferramentas
        calls = response.choices[0].message.tool_calls  

        # Registra a mensagem do assistente no histórico
        llm_client.add_assistant_message({
            "content": tool_reply,
            "tool_calls": calls,
            "role": "assistant"
        })

        # Processa cada chamada de ferramenta
        for call in calls:
            with st.chat_message(name="tool", avatar=":material/build:"):
                st.markdown(f'LLM chamando tool {call.function.name}')
                with st.expander("Visualizar argumentos"):
                    st.code(call.function.arguments)

            # Executa a tool
            with st.spinner(f"Processando chamada para {call.function.name}..."):
                result = process_single_tool_call(call)

            # Exibe o resultado da tool
            with st.chat_message(name="tool", avatar=":material/data_object:"):
                with st.expander("Visualizar resposta"):
                    st.code(result)

            # Registra a resposta da tool no histórico
            llm_client.add_tool_message({
                "tool_call_id": call.id,
                "content": result,
                "role": "tool"
            })

        # Solicita ao LLM a resposta final após uso das tools
        with st.spinner("Gerando resposta final..."):
            next_response = llm_client.complete_chat(tools)

        # Resolve recursivamente até não haver mais tool calls
        resolve_chat(next_response)
    
    else:
        # Caso normal: resposta final do assistente
        assistant_reply = response.choices[0].message.content

        with st.chat_message("assistant"):
            st.markdown(assistant_reply)

        # Salva a resposta no histórico
        llm_client.add_assistant_message({
            "content": assistant_reply,
            "role": "assistant"
        })

# Renderiza o histórico de mensagens da conversa
for message in st.session_state.llmClient.history:
    if message["role"] != "tool":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

        # Exibe chamadas de tools associadas a mensagens do assistente
        if message["role"] == 'assistant' and "tool_calls" in message and message["tool_calls"]:
            for call in message["tool_calls"]:
                with st.chat_message(name="tool", avatar=":material/build:"):
                    st.markdown(f'LLM chamando tool {call.function.name}')
                    with st.expander("Visualizar resultado"):
                        st.code(call.function.arguments)
    else:
        # Exibe respostas das tools
        with st.chat_message(name="tool", avatar=":material/data_object:"):
            with st.expander("Visualizar resposta"):
                st.code(message["content"])

# Campo de entrada do usuário
prompt = st.chat_input("Digite sua pergunta:")

# Fluxo principal quando o usuário envia uma pergunta
if prompt:
    llm_client = st.session_state.llmClient
    llm_client.add_user_message(prompt)  # Salva mensagem do usuário no histórico
    st.chat_message("user").markdown(prompt)

    with st.container():
        with st.spinner("Processando sua pergunta..."):
            # Envia a pergunta ao LLM
            response = llm_client.complete_chat(st.session_state.tools)
            # Processa a resposta (com ou sem tools)
            resolve_chat(response)  