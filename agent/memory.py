"""
Memory module for the AI Research Agent.
Provides persistent storage using SQLite for agent memory.
"""
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from agent import config
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class Memory:
    """
    A SQLite-based memory system for the AI Research Agent.
    
    This class provides methods to store, retrieve, and search memories,
    including conversation history, facts, and document references.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory system with the specified database path.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses the default from config.
        """
        if db_path is None:
            db_path = config.DB_PATH
        
        # Ensure the parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._initialize_database()
        
        logger.info(f"Initialized Memory with database at {self.db_path}")
    
    def _initialize_database(self):
        """
        Set up the database tables if they don't exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create table for conversation memory
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT
            )
            ''')
            
            # Create table for facts and knowledge
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                metadata TEXT
            )
            ''')
            
            # Create table for document references
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT,
                metadata TEXT
            )
            ''')
            
            # Create indexes for faster searching
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_facts_timestamp ON facts(timestamp)')
            
            conn.commit()
    
    def write_memory(
        self, 
        memory_type: str, 
        content: Dict[str, Any]
    ) -> int:
        """
        Write a memory to the database.
        
        Args:
            memory_type: Type of memory ('conversation', 'fact', or 'document')
            content: Dictionary containing the memory content
            
        Returns:
            ID of the inserted memory
        """
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if memory_type == 'conversation':
                # Extract required fields
                session_id = content.get('session_id', 'default')
                role = content.get('role', 'unknown')
                message_content = content.get('content', '')
                
                # Extract metadata
                metadata = {k: v for k, v in content.items() 
                           if k not in ['session_id', 'role', 'content']}
                
                cursor.execute(
                    '''
                    INSERT INTO conversations 
                    (timestamp, session_id, role, content, metadata) 
                    VALUES (?, ?, ?, ?, ?)
                    ''', 
                    (timestamp, session_id, role, message_content, json.dumps(metadata))
                )
                
            elif memory_type == 'fact':
                # Extract required fields
                fact = content.get('fact', '')
                source = content.get('source', '')
                confidence = content.get('confidence', 1.0)
                
                # Extract metadata
                metadata = {k: v for k, v in content.items() 
                           if k not in ['fact', 'source', 'confidence']}
                
                cursor.execute(
                    '''
                    INSERT INTO facts 
                    (timestamp, fact, source, confidence, metadata) 
                    VALUES (?, ?, ?, ?, ?)
                    ''', 
                    (timestamp, fact, source, confidence, json.dumps(metadata))
                )
                
            elif memory_type == 'document':
                # Extract required fields
                title = content.get('title', 'Untitled')
                doc_content = content.get('content', '')
                url = content.get('url', '')
                
                # Extract metadata
                metadata = {k: v for k, v in content.items() 
                           if k not in ['title', 'content', 'url']}
                
                cursor.execute(
                    '''
                    INSERT INTO documents 
                    (timestamp, title, content, url, metadata) 
                    VALUES (?, ?, ?, ?, ?)
                    ''', 
                    (timestamp, title, doc_content, url, json.dumps(metadata))
                )
                
            else:
                logger.error(f"Invalid memory type: {memory_type}")
                return -1
            
            # Get the ID of the inserted row
            inserted_id = cursor.lastrowid
            conn.commit()
            
            logger.debug(f"Wrote memory of type {memory_type} with ID {inserted_id}")
            return inserted_id
    
    def read_memory(
        self, 
        memory_type: str, 
        memory_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Read a specific memory by ID.
        
        Args:
            memory_type: Type of memory ('conversation', 'fact', or 'document')
            memory_id: ID of the memory to retrieve
            
        Returns:
            Dictionary containing the memory content, or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if memory_type == 'conversation':
                cursor.execute('SELECT * FROM conversations WHERE id = ?', (memory_id,))
                
            elif memory_type == 'fact':
                cursor.execute('SELECT * FROM facts WHERE id = ?', (memory_id,))
                
            elif memory_type == 'document':
                cursor.execute('SELECT * FROM documents WHERE id = ?', (memory_id,))
                
            else:
                logger.error(f"Invalid memory type: {memory_type}")
                return None
                
            row = cursor.fetchone()
            
            if row is None:
                logger.warning(f"No memory found with type {memory_type} and ID {memory_id}")
                return None
                
            # Convert row to dictionary
            result = dict(row)
            
            # Parse JSON metadata if present
            if 'metadata' in result and result['metadata']:
                result['metadata'] = json.loads(result['metadata'])
                
            logger.debug(f"Read memory of type {memory_type} with ID {memory_id}")
            return result
    
    def search_memory(
        self, 
        memory_type: str, 
        query: str = "", 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories by content with optional filters.
        
        Args:
            memory_type: Type of memory ('conversation', 'fact', or 'document')
            query: Search text to match in content
            filters: Dictionary of field-value pairs to filter results
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing matching memories
        """
        filters = filters or {}
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Start building the query
            if memory_type == 'conversation':
                base_query = 'SELECT * FROM conversations WHERE 1=1'
                content_field = 'content'
                
            elif memory_type == 'fact':
                base_query = 'SELECT * FROM facts WHERE 1=1'
                content_field = 'fact'
                
            elif memory_type == 'document':
                base_query = 'SELECT * FROM documents WHERE 1=1'
                content_field = 'content'
                
            else:
                logger.error(f"Invalid memory type: {memory_type}")
                return []
            
            # Build conditions and parameters
            conditions = []
            params = []
            
            # Add text search if query is provided
            if query:
                conditions.append(f"{content_field} LIKE ?")
                params.append(f"%{query}%")
            
            # Add filters
            for field, value in filters.items():
                if field in ['session_id', 'role', 'source', 'title', 'url']:
                    conditions.append(f"{field} = ?")
                    params.append(value)
            
            # Complete the query
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            # Add order and limit
            base_query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            results = []
            for row in rows:
                item = dict(row)
                
                # Parse JSON metadata if present
                if 'metadata' in item and item['metadata']:
                    try:
                        item['metadata'] = json.loads(item['metadata'])
                    except json.JSONDecodeError:
                        item['metadata'] = {}
                        
                results.append(item)
            
            logger.debug(f"Searched {memory_type} memories with query '{query}', found {len(results)} results")
            return results
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for a specific session.
        
        Args:
            session_id: ID of the conversation session
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries in OpenAI format (role, content)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                SELECT role, content FROM conversations 
                WHERE session_id = ? 
                ORDER BY timestamp ASC 
                LIMIT ?
                ''',
                (session_id, limit)
            )
            
            rows = cursor.fetchall()
            
            # Format as OpenAI messages
            messages = [{"role": row["role"], "content": row["content"]} for row in rows]
            
            logger.debug(f"Retrieved {len(messages)} messages from session {session_id}")
            return messages
    
    def delete_memory(self, memory_type: str, memory_id: int) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_type: Type of memory ('conversation', 'fact', or 'document')
            memory_id: ID of the memory to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if memory_type == 'conversation':
                cursor.execute('DELETE FROM conversations WHERE id = ?', (memory_id,))
                
            elif memory_type == 'fact':
                cursor.execute('DELETE FROM facts WHERE id = ?', (memory_id,))
                
            elif memory_type == 'document':
                cursor.execute('DELETE FROM documents WHERE id = ?', (memory_id,))
                
            else:
                logger.error(f"Invalid memory type: {memory_type}")
                return False
            
            if cursor.rowcount > 0:
                logger.info(f"Deleted memory of type {memory_type} with ID {memory_id}")
                return True
            else:
                logger.warning(f"No memory found to delete with type {memory_type} and ID {memory_id}")
                return False 