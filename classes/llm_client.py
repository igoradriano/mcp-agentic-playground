import openai
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

class LLmClient:
    """
    Cliente de alto nível para interação com modelos de linguagem (LLMs)
    utilizando a API de Chat Completions da OpenAI.

    Responsabilidades:
    - Manter o histórico da conversa (mensagens do usuário, assistente e tools)
    - Encapsular a chamada ao modelo
    - Facilitar o uso de ferramentas (tools) no fluxo de chat
    """

    def __init__(self, model: str):
        """
        Inicializa o cliente do LLM.
        :param model: Nome do modelo a ser utilizado (ex: 'gpt-4.1', 'gpt-4o', etc.)
        """
        self.model = model
        self.history: list[ChatCompletionMessageParam] = []   # Histórico completo da conversa no formato esperado pela OpenAI. Inclui mensagens de usuário, assistente e ferramentas

    def add_user_message(self, message: str):
        """
        Adiciona uma mensagem do usuário ao histórico.
        :param message: Texto enviado pelo usuário
        """
        self.history.append(
            ChatCompletionUserMessageParam(
                content=message,
                role="user"
            )
        )

    def add_assistant_message(self, message: ChatCompletionAssistantMessageParam):
        """
        Adiciona uma mensagem do assistente (LLM) ao histórico.
        Normalmente utilizada após uma resposta do modelo,
        preservando o contexto para próximas interações.
        :param message: Mensagem gerada pelo assistente
        """
        self.history.append(message)
        
    def add_tool_message(self, message: ChatCompletionToolMessageParam):
        """
        Adiciona ao histórico a resposta de uma ferramenta (tool).
        Isso é essencial em arquiteturas com agentes, onde:
        - O LLM decide chamar uma tool
        - A aplicação executa a tool
        - O resultado da tool é devolvido ao LLM como contexto
        :param message: Mensagem de retorno da ferramenta
        """
        self.history.append(message)
        
    def complete_chat(self, tools=[] ) -> ChatCompletion:
        """
        Executa a chamada ao modelo de chat da OpenAI, considerando
        todo o histórico acumulado e as ferramentas disponíveis.
        :param tools: Lista opcional de tools (funções) disponíveis para o modelo
        :return: Objeto ChatCompletion com a resposta do modelo
        """
        return openai.chat.completions.create(
            model=self.model, # Modelo configurado na inicialização
            messages=self.history, # Histórico completo da conversa
            tools=tools, # Definição das ferramentas que o modelo pode chamar
            tool_choice="auto", # Permite que o modelo decida automaticamente se deve ou não chamar uma ferramenta
            parallel_tool_calls=False  # Impede múltiplas chamadas de tools em paralelo, facilitando controle e rastreabilidade (importante em MCP)
        )