import logging 
import json
import time
import threading
import os
from datetime import datetime, timezone 
from functools import wraps
from dotenv import load_dotenv
from contextlib import contextmanager
from typing import Callable, Any, Optional 
from langsmith import traceable
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

load_dotenv()


class JsonFormatter(logging.Formatter): # for tlogging and parsing

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            # "line_no": record.lineno,
        }

        if hasattr(record, "extra_data"):
            log_record["extra_data"] = record.extra_data
        return json.dumps(log_record)


def gLogger(name:str = " RAGProd") -> logging.Logger:
        logger = logging.getLogger(name)

        if not logger.handlers: # hashandlers()
            logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
        return logger


@contextmanager
def RequestTimer():
    start_time = time.perf_counter()
    # Create a simple container to hold the latency result
    timer = {"elapsed_ms": 0.0}
    try:
        yield timer
    finally:
        end_time = time.perf_counter()
        timer["elapsed_ms"] = (end_time - start_time) * 1000


class Metrics:  #to collect application ,metric
    """ Need to replace with prometheus or other metric collection system"""

    def __init__(self):
        self.metrics = {

            "total_requests": 0,
            "total_errors": 0,
            "total_ip_tokens": 0,
            "total_op_tokens": 0,
            "total_latency_ms": 0.0,
            "latency_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self._lock = threading.Lock()

    def record_request(
            self, ip_tokens:int = 0, op_tokens:int = 0, latency_ms:float = 0.0,
            error:bool=False, cache_hit:bool=False
            ) -> None:
        with self._lock:
            self.metrics["total_requests"] += 1
            self.metrics["total_ip_tokens"] += ip_tokens
            self.metrics["total_op_tokens"] += op_tokens
            self.metrics["total_latency_ms"] += latency_ms
            self.metrics["latency_count"] += 1
            if error:
                self.metrics["total_errors"] += 1
            if cache_hit:
                self.metrics["cache_hits"] += 1
            else:
                self.metrics["cache_misses"] += 1

    def get_summary(self) -> dict:
        with self._lock:
            current = self.metrics.copy()
        avg_latency = current["total_latency_ms"] / current["latency_count"] if current["latency_count"] else 0.0
        error_rate = current["total_errors"] / current["total_requests"] if current["total_requests"] else 0.0
        cache_total = current["cache_hits"] + current["cache_misses"]
        cache_hit_rate = current["cache_hits"] / cache_total if cache_total else 0.0
        return {
            "tot_reqs": current["total_requests"],
            "tot_err": current["total_errors"],
            "tot_ip_tokens": current["total_ip_tokens"],
            "tot_op_tokens": current["total_op_tokens"],
            "avg_latency": round(avg_latency, 2),
            "cache_hits": f"{cache_hit_rate:.2%}",
            "err_rate": f"{error_rate:.2%}"
        }


class LLMmon:
    def __init__(self):
        self.metrics = Metrics()
        self.llm = ChatGoogleGenerativeAI (model="gemini-3.1-flash-lite")
        self.logger = gLogger("LLMmon")


    @traceable(name="LLM call monitoring")
    def  monitor_call(self,query:str) -> str:
        start_time = time.time()
        error = False
        try:
            response = self.llm.invoke(query)
            latency_ms = (time.time() - start_time) * 1000
            usage = response.response_metadata.get("usage_metadata", {})
            ip_tokens = usage.get("prompt_token_count", len(query.split()) * 4 // 3)
            op_tokens = usage.get("candidates_token_count", usage.get("output_tokens", 0))
            self.metrics.record_request(ip_tokens, op_tokens, latency_ms,False,False)
            self.logger.info(f"LLM call successful. Latency: {latency_ms:.2f} ms, IP tokens: {ip_tokens}, OP tokens: {op_tokens}", 
                            extra={
                                "extra_data": 
                                    {   
                                        "latency_ms": latency_ms, 
                                        "input_tokens": ip_tokens, 
                                        "output_tokens": op_tokens}})
            return response.content
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(0, 0, latency_ms, error=True)
            self.logger.error(f"LLM call failed. Latency: {latency_ms:.2f} ms, Error: {str(e)}")
            raise
        
        
        
def monitoring():
    llm = LLMmon()
    print("demo     monitoring")
    
    query = ["What is the capital of France?", "What is the largest planet in our solar system?"]
    
    try:
       
        for q in query:
            response = llm.monitor_call(q)
            print(f"Query: {q}\nResponse: {response.content}\n")
            
            summary = llm.metrics.get_summary()
            print("Metrics Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error during LLM call: {str(e)}")
        
        
if __name__ == "__main__":
    monitoring()
