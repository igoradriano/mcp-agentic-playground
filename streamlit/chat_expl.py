# =========================
# CONFIGURAÇÃO DE PATH
# =========================

# Importa os módulos padrão do Python para interação com o sistema operacional
import sys, os

# Adiciona o diretório pai do arquivo atual ao sys.path
# Isso permite importar módulos locais (ex: pasta "classes/")
# sem precisar instalar o projeto como um pacote Python
sys.path.append(
    os.path.abspath(                      # Converte o caminho para absoluto
        os.path.join(
            os.path.dirname(__file__),    # Diretório onde este arquivo está
            '..'                           # Diretório pai
        )
    )
)

# =========================
# IMPORTS DE UI E CONFIG
# =========================

# Importa o Streamlit, framework responsável pela interface web e gerenciamento de estado
import streamlit as st

# Importa função para carregar variáveis de ambiente do arquivo .env
from dotenv import load_dotenv

# =========================
# IMPORTS DE DOMÍNIO (LLM e MCP)
# =========================

# Cliente responsável por:
# - Manter histórico da conversa
# - Enviar mensagens ao LLM
# - Receber respostas e tool calls
from classes.llm_client import LLmClient  

# Cliente responsável por:
# - Inicializar o MCP (Model Context Protocol)
# - Descobrir ferramentas disponíveis
# - Executar chamadas de ferramentas via stdio
from classes.mcp_client import McpClient  

# =========================
# IMPORTS AUXILIARES
# =========================

# asyncio: execução assíncrona
# sys: informações do sistema operacional
# json: serialização/deserialização de argumentos das tools
import asyncio, sys, json  

# =========================
# CONFIGURAÇÃO DO MCP
# =========================

# Caminho do script que implementa o servidor MCP
# Esse script expõe ferramentas (ex: SQL) para o LLM
tool = "servers/server_sql.py"

# =========================
# CORREÇÃO ESPECÍFICA PARA WINDOWS
# =========================

# No Windows, o event loop padrão pode causar problemas
# com subprocessos e comunicação via stdio (usado pelo MCP)
# Essa política garante compatibilidade com asyncio + subprocess
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

# =========================
# UI – CABEÇALHO
# =========================

# Renderiza um título centralizado usando HTML
# unsafe_allow_html=True permite usar HTML diretamente
st.markdown(
    "<h1 style='text-align: center;'>NovoDive Motors</h1>",
    unsafe_allow_html=True
)

# =========================
# UI – LAYOUT EM COLUNAS
# =========================

# Cria três colunas na interface
left_co, cent_co, last_co = st.columns(3)

# Usa apenas a coluna central para exibir o logo
with cent_co:
    # Exibe imagem com legenda
    st.image(
        "arquivos/novadrive.png",
        caption="NovaDrive Motors"
    )

# =========================
# INICIALIZAÇÃO DO LLM (STATEFUL)
# =========================

# Verifica se o cliente LLM já existe no estado da sessão
# Isso evita recriar o LLM a cada interação
if "llmClient" not in st.session_state:
    
    # Carrega variáveis do .env (ex: OPENAI_API_KEY)
    load_dotenv()  
    
    # Cria uma instância do cliente LLM
    # O modelo é definido explicitamente
    st.session_state.llmClient = LLmClient(
        "gpt-4-1106-preview"
    )

# =========================
# FUNÇÃO UTILITÁRIA SYNC → ASYNC
# =========================

# Essa função permite executar código assíncrono
# dentro de um ambiente síncrono (Streamlit)
def run_task(coro):
    
    # Cria um novo event loop asyncio
    loop = asyncio.new_event_loop()
    
    # Define esse loop como o loop atual da thread
    asyncio.set_event_loop(loop)
    
    # Registra a corrotina como uma task
    task = loop.create_task(coro)
    
    # Executa a task até finalizar (bloqueante)
    return loop.run_until_complete(
        asyncio.wait_for(task, timeout=None)
    )

# =========================
# DESCOBERTA DE FERRAMENTAS (TOOLS)
# =========================

# Inicializa as ferramentas apenas uma vez por sessão
if "tools" not in st.session_state:
    
    # Exibe spinner enquanto as ferramentas são carregadas
    with st.spinner("Lendo ferramentas..."): 
        try:
            
            # Função assíncrona para inicializar o MCP
            async def init_mcp():
                
                # Cria cliente MCP
                client = McpClient() 
                
                # Inicializa o MCP via stdio,
                # executando o script server_sql.py
                await client.initialize_with_stdio(
                    "mcp",
                    ["run", tool]
                )
                
                # Pequena espera para garantir que o processo esteja pronto
                await asyncio.sleep(1)
                
                # Obtém a lista de tools do MCP
                # e formata no schema esperado pelo LLM
                tools = client.format_tools_llm(
                    await client.get_tools()
                )
                
                # Finaliza corretamente o cliente MCP
                await client.cleanup()
                
                # Retorna as tools prontas para uso
                return tools
            
            # Executa a inicialização async de forma síncrona
            st.session_state.tools = run_task(init_mcp())
            
            # Feedback visual de sucesso
            st.success("Ferramentas lidas com sucesso!")
        
        except Exception as e:
            # Exibe erro e interrompe a aplicação
            st.error(f"Erro ao utilizar MCP Client: {str(e)}")
            st.stop()

# =========================
# EXECUÇÃO DE UMA TOOL
# =========================

# Processa UMA chamada de ferramenta solicitada pelo LLM
def process_single_tool_call(call):
    try:
        
        # Função assíncrona responsável pela execução da tool
        async def do_call():
            
            # Cria cliente MCP
            client = McpClient()
            
            # Inicializa MCP apontando para o servidor de tools
            await client.initialize_with_stdio(
                "mcp",
                ["run", tool]
            )
            
            # Executa a ferramenta solicitada pelo LLM
            # call.function.name → nome da tool
            # call.function.arguments → argumentos em JSON (string)
            tool_result = await client.call_tool(
                call.function.name,
                json.loads(call.function.arguments)
            )
            
            # Finaliza o cliente MCP
            await client.cleanup()
            
            return tool_result

        # Executa a função assíncrona
        call_result = run_task(do_call())

        # Extrai apenas partes textuais da resposta da tool
        # (ignora metadata ou outros tipos)
        return ''.join(
            item.text
            for item in call_result.content
            if item.type == 'text'
        )
    
    except Exception as e:
        # Retorna erro em formato de texto para o LLM
        return f"Error calling tool: {str(e)}"

# =========================
# ORQUESTRADOR PRINCIPAL DO CHAT
# =========================

def resolve_chat(response):
    
    # Recupera cliente LLM da sessão
    llm_client = st.session_state.llmClient
    
    # Recupera ferramentas disponíveis
    tools = st.session_state.tools

    # Verifica se o LLM solicitou chamadas de tools
    if response.choices[0].finish_reason == 'tool_calls':
        
        # Conteúdo textual inicial do LLM (se existir)
        tool_reply = response.choices[0].message.content

        # Exibe resposta parcial do assistente
        if tool_reply is not None:
            with st.chat_message("assistant"):
                st.markdown(tool_reply)

        # Lista de chamadas de ferramentas solicitadas
        calls = response.choices[0].message.tool_calls

        # Salva mensagem do assistente no histórico
        llm_client.add_assistant_message({
            "content": tool_reply,
            "tool_calls": calls,
            "role": "assistant"
        })

        # Executa cada chamada de ferramenta
        for call in calls:
            
            # Exibe visualmente que o LLM chamou uma tool
            with st.chat_message(name="tool", avatar=":material/build:"):
                st.markdown(f'LLM chamando tool {call.function.name}')
                with st.expander("Visualizar argumentos"):
                    st.code(call.function.arguments)

            # Executa a tool
            with st.spinner(
                f"Processando chamada para {call.function.name}..."
            ):
                result = process_single_tool_call(call)

            # Exibe o resultado retornado pela tool
            with st.chat_message(name="tool", avatar=":material/data_object:"):
                with st.expander("Visualizar resposta"):
                    st.code(result)

            # Salva resposta da tool no histórico
            llm_client.add_tool_message({
                "tool_call_id": call.id,
                "content": result,
                "role": "tool"
            })

        # Solicita nova resposta ao LLM,
        # agora com os resultados das tools no contexto
        with st.spinner("Gerando resposta final..."):
            next_response = llm_client.complete_chat(tools)

        # Chamada recursiva até não haver mais tool calls
        resolve_chat(next_response)

    else:
        # Caso o LLM tenha retornado uma resposta final
        assistant_reply = response.choices[0].message.content

        # Exibe resposta do assistente
        with st.chat_message("assistant"):
            st.markdown(assistant_reply)

        # Salva no histórico
        llm_client.add_assistant_message({
            "content": assistant_reply,
            "role": "assistant"
        })

# =========================
# RENDERIZAÇÃO DO HISTÓRICO
# =========================

# Percorre todo o histórico de mensagens
for message in st.session_state.llmClient.history:
    
    if message["role"] != "tool":
        
        # Exibe mensagens do usuário e do assistente
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

        # Se a mensagem do assistente tiver tool calls associadas
        if (
            message["role"] == 'assistant'
            and "tool_calls" in message
            and message["tool_calls"]
        ):
            for call in message["tool_calls"]:
                with st.chat_message(
                    name="tool",
                    avatar=":material/build:"
                ):
                    st.markdown(
                        f'LLM chamando tool {call.function.name}'
                    )
                    with st.expander("Visualizar resultado"):
                        st.code(call.function.arguments)
    else:
        # Exibe mensagens retornadas pelas tools
        with st.chat_message(
            name="tool",
            avatar=":material/data_object:"
        ):
            with st.expander("Visualizar resposta"):
                st.code(message["content"])

# =========================
# INPUT DO USUÁRIO
# =========================

# Campo de texto para o usuário digitar perguntas
prompt = st.chat_input("Digite sua pergunta:")

# =========================
# FLUXO PRINCIPAL
# =========================

# Executa quando o usuário envia uma pergunta
if prompt:
    
    llm_client = st.session_state.llmClient
    
    # Salva mensagem do usuário no histórico
    llm_client.add_user_message(prompt)
    
    # Exibe mensagem do usuário no chat
    st.chat_message("user").markdown(prompt)

    with st.container():
        with st.spinner("Processando sua pergunta..."):
            
            # Envia a conversa ao LLM
            response = llm_client.complete_chat(
                st.session_state.tools
            )
            
            # Processa a resposta (com ou sem tools)
            resolve_chat(response)