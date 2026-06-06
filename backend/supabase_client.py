# supabase_client.py
# PostgreSQL Direct Connection (Approach 2)
# Replaces Supabase REST client with psycopg2
# FIXED: score → health_score

import os
import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PostgresManager:
    """Direct PostgreSQL connection manager using psycopg2"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_url = os.getenv("DATABASE_URL")
        
        if not self.db_url:
            raise ValueError("Missing DATABASE_URL environment variable")
        
        self.connection = None
        self._connect()
        self._initialized = True
    
    def _connect(self):
        """Connect to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            logger.info("✅ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    def execute_query(self, query: str, params=None):
        """Execute a single query"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Query error: {e}")
            raise
    
    def fetch_query(self, query: str, params=None):
        """Fetch results from query"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise
    
    def upsert_companies(self, companies: List[Dict]):
        """Insert/Update companies"""
        if not companies:
            return
        
        cursor = self.connection.cursor()
        
        query = """
        INSERT INTO companies (ticker, health_score, tags)
        VALUES (%s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            health_score = EXCLUDED.health_score,
            tags = EXCLUDED.tags,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            data = [(c["ticker"], c.get("health_score"), c.get("tags")) for c in companies]
            execute_batch(cursor, query, data, page_size=100)
            self.connection.commit()
            logger.info(f"✅ Upserted {len(companies)} companies")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Upsert companies error: {e}")
            raise
        finally:
            cursor.close()
    
    def get_company_id(self, ticker: str) -> int:
        """Get company_id by ticker"""
        query = "SELECT id FROM companies WHERE ticker = %s"
        result = self.fetch_query(query, (ticker,))
        return result[0][0] if result else None
    
    def upsert_daily_metrics(self, metrics: List[Dict]):
        """Insert/Update daily metrics"""
        if not metrics:
            return
        
        cursor = self.connection.cursor()
        
        query = """
        INSERT INTO daily_metrics (
            company_id, run_date,
            open, high, low, close, adj_close, volume,
            ltp, trend_status, sma_50, sma_200,
            rsi_14, momentum_status,
            weighted_avg, distance_pct, distance_status,
            current_volume, avg_volume_20d, relative_volume, volume_strength,
            swing_score, setup_type
        ) VALUES (
            %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        )
        ON CONFLICT (company_id, run_date) DO UPDATE SET
            ltp = EXCLUDED.ltp,
            trend_status = EXCLUDED.trend_status,
            sma_50 = EXCLUDED.sma_50,
            sma_200 = EXCLUDED.sma_200,
            rsi_14 = EXCLUDED.rsi_14,
            momentum_status = EXCLUDED.momentum_status,
            weighted_avg = EXCLUDED.weighted_avg,
            distance_pct = EXCLUDED.distance_pct,
            distance_status = EXCLUDED.distance_status,
            current_volume = EXCLUDED.current_volume,
            avg_volume_20d = EXCLUDED.avg_volume_20d,
            relative_volume = EXCLUDED.relative_volume,
            volume_strength = EXCLUDED.volume_strength,
            swing_score = EXCLUDED.swing_score,
            setup_type = EXCLUDED.setup_type,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            data = []
            for m in metrics:
                row = (
                    m["company_id"], m["run_date"],
                    m.get("open"), m.get("high"), m.get("low"), m.get("close"), 
                    m.get("adj_close"), m.get("volume"),
                    m.get("ltp"), m.get("trend_status"), m.get("sma_50"), m.get("sma_200"),
                    m.get("rsi_14"), m.get("momentum_status"),
                    m.get("weighted_avg"), m.get("distance_pct"), m.get("distance_status"),
                    m.get("current_volume"), m.get("avg_volume_20d"), 
                    m.get("relative_volume"), m.get("volume_strength"),
                    m.get("swing_score"), m.get("setup_type")
                )
                data.append(row)
            
            execute_batch(cursor, query, data, page_size=100)
            self.connection.commit()
            logger.info(f"✅ Upserted {len(metrics)} daily metrics")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Upsert metrics error: {e}")
            raise
        finally:
            cursor.close()
    
    def close(self):
        """Close connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")


def get_db() -> PostgresManager:
    """Get database manager instance"""
    return PostgresManager()
