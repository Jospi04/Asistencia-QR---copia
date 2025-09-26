import mysql.connector
from mysql.connector import Error
import os
from typing import Optional

class MySQLConnection:
    def __init__(self):
        # 🔹 Configuración para AWS RDS
        # Usa variables de entorno para no exponer credenciales en el código
        self.host = os.getenv('DB_HOST', 'joseph.cjows6c2y07g.us-east-2.rds.amazonaws.com')  # Endpoint de RDS
        self.port = os.getenv('DB_PORT', '3306')                          # Puerto por defecto
        self.database = os.getenv('DB_NAME', 'sistema_asistencia_qr')     # Nombre de la BD en AWS
        self.user = os.getenv('DB_USER', 'admin')                         # Usuario configurado en RDS
        self.password = os.getenv('DB_PASSWORD', 'Vikyvaleria.24')           # Contraseña configurada en RDS
        self.connection = None
    
    def connect(self) -> Optional[mysql.connector.MySQLConnection]:
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                autocommit=True,
                use_unicode=True,
                auth_plugin='mysql_native_password'
            )
            if self.connection.is_connected():
                print(f"✅ Conexión exitosa a MySQL en AWS RDS - Base de datos: {self.database}")
                return self.connection
        except Error as e:
            print(f"❌ Error al conectar a MySQL en AWS RDS: {e}")
            print(f"Credenciales usadas - Host: {self.host}:{self.port}, User: {self.user}, DB: {self.database}")
            return None
    
    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔒 Conexión a MySQL (AWS RDS) cerrada")
    
    def get_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        if not self.connection or not self.connection.is_connected():
            return self.connect()
        return self.connection
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"⚠️ Error ejecutando query en AWS: {e}")
            return None
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        connection = self.get_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            cursor.close()
            return True
        except Error as e:
            print(f"⚠️ Error ejecutando update en AWS: {e}")
            connection.rollback()
            return False
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[int]:
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
        except Error as e:
            print(f"⚠️ Error ejecutando insert en AWS: {e}")
            connection.rollback()
            return None


# --- Instancia global y función helper ---
_db_instance = MySQLConnection()

def get_connection() -> Optional[mysql.connector.MySQLConnection]:
    """Devuelve una conexión activa a la BD en AWS"""
    return _db_instance.get_connection()
