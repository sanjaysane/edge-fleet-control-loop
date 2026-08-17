"""
On-call simulator - tiny HTTP server that pages from alert_manager
"""
from fastapi import FastAPI
import time, json
app=FastAPI()
pages=[]

@app.post("/oncall/page")
def page(alert: dict):
    pages.append(alert)
    print(f"PAGING oncall for {alert['rule']}: {alert['msg']}")
    return {"acked": False, "pages": len(pages)}

@app.get("/oncall/pages")
def list_pages():
    return pages
