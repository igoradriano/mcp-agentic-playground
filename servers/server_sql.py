from mcp.server.fastmcp import FastMCP
import psycopg2, json
import os

# Inicializa o servidor MCP com nome lógico "SQL"
# Declara a dependência psycopg2 para execução das tools
mcp = FastMCP("SQL", dependencies=["psycopg2"])

# ------------------------------------------------------------------
# Configurações de conexão com o banco PostgreSQL
# ------------------------------------------------------------------
SERVER = os.getenv("MCP_SQL_HOST", "143.244.215.137")
PORT = os.getenv("MCP_SQL_PORT", "5432")
DATABASE = os.getenv("MCP_SQL_DATABASE", "novadrive")
USERNAME = os.getenv("MCP_SQL_USER", "etlreadonly")
PASSWORD = os.getenv("MCP_SQL_PASSWORD", "novadrive376A@")

# Parâmetros consolidados de conexão
CONN_STR = {
    "host": SERVER,
    "port": PORT,
    "dbname": DATABASE,
    "user": USERNAME,
    "password": PASSWORD,
}

# Cria e retorna uma nova conexão com o banco
def get_connection():
    return psycopg2.connect(**CONN_STR)

# ------------------------------------------------------------------
# TOOL: Descoberta de schema do banco
# ------------------------------------------------------------------
@mcp.tool()
def get_schema():
    """Retorna tabelas e colunas do schema público"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Consulta metadados das tabelas e colunas
        cursor.execute("""
            SELECT 
                table_name, 
                column_name, 
                data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)
        
        # Organiza o schema por tabela
        schema = {}
        for table_name, column_name, data_type in cursor.fetchall():
            if table_name not in schema:
                schema[table_name] = []
            schema[table_name].append({
                "column": column_name,
                "type": data_type
            })

        cursor.close()
        conn.close()
        
        # Retorna o schema em JSON legível
        return json.dumps({"schema": schema}, indent=4, sort_keys=True, default=str)
    except Exception as e:
        return {"error": str(e)}

# ------------------------------------------------------------------
# TOOL: Verificação de saúde da conexão
# ------------------------------------------------------------------
@mcp.tool()
def health_check() -> bool:
    """Verifica se o banco está acessível"""
    try:
        conn = get_connection()
        conn.close()
        return True
    except:
        return False

# ------------------------------------------------------------------
# TOOL: Execução de consultas SQL
# ------------------------------------------------------------------
@mcp.tool()
def query(sql: str) -> str:
    """Executa uma query SQL e retorna o resultado"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Executa a SQL recebida
        cursor.execute(sql)
        rows = cursor.fetchall()

        # Converte resultado em lista de dicionários
        result = [
            dict(zip([desc[0] for desc in cursor.description], row))
            for row in rows
        ]

        cursor.close()
        conn.close()

        # Retorna os dados em JSON
        return json.dumps(result, indent=4, sort_keys=True, default=str)
    except Exception as e:
        return str(e)