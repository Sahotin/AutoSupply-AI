from typing import Any
import httpx
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from .indexing import embedding_model
from .config import settings

class BusinessTools:
    def __init__(self, client: httpx.Client | None=None): self.client=client or httpx.Client(base_url=settings.business_url,timeout=10)
    def get(self,path:str)->dict[str,Any]: r=self.client.get(path); r.raise_for_status(); return r.json()
    def batch_context(self,n:str): return self.get(f"/batches/{n}/context")
    def part_impact(self,n:str): return self.get(f"/parts/{n}/impact")
    def quality_case(self,n:str): return self.get(f"/quality-cases/{n}")
    def create_action(self,n:str,payload:dict): r=self.client.post(f"/quality-cases/{n}/actions",json=payload); r.raise_for_status(); return r.json()

class GraphTools:
    def impact(self,part_number:str)->list[dict]:
        driver=GraphDatabase.driver(settings.neo4j_uri,auth=(settings.neo4j_user,settings.neo4j_password))
        try:
            q="MATCH (p:Part {partNumber:$part})<-[:USES]-(v:VehicleModel) RETURN v.modelCode AS model, v.name AS name"
            return [dict(x) for x in driver.execute_query(q,part=part_number,database_="neo4j").records]
        finally: driver.close()
    def batch_impact(self,batch_number:str)->list[dict]:
        driver=GraphDatabase.driver(settings.neo4j_uri,auth=(settings.neo4j_user,settings.neo4j_password))
        try:
            q="MATCH (b:Batch {batchNumber:$batch})-[:CONTAINS]->(:Part)<-[:USES]-(v:VehicleModel) RETURN v.modelCode AS model, v.name AS name"
            return [dict(x) for x in driver.execute_query(q,batch=batch_number,database_="neo4j").records]
        finally: driver.close()
    def supplier_dependency(self,supplier_code:str)->list[dict]:
        driver=GraphDatabase.driver(settings.neo4j_uri,auth=(settings.neo4j_user,settings.neo4j_password))
        try:
            q="MATCH (s:Supplier {code:$supplier})-[:SUPPLIES]->(p:Part) RETURN p.partNumber AS part, p.name AS name"
            return [dict(x) for x in driver.execute_query(q,supplier=supplier_code,database_="neo4j").records]
        finally: driver.close()

class DocumentTools:
    def search(self,query:str,limit:int=4)->list[dict]:
        client=QdrantClient(url=settings.qdrant_url)
        vector=next(embedding_model().embed([query])).tolist()
        points=client.query_points(collection_name="factoryops_documents",query=vector,limit=limit).points
        return [{"id":str(x.payload["id"]),"score":x.score,"text":x.payload.get("text","")} for x in points]
