from extraction_agent import get_client
from config import EXTRACTION_AGENT_ID
r = get_client().inference.chat({'user_id':'test@demo.com','agent_id':EXTRACTION_AGENT_ID,'session_id':'test-session-1','message':'Say hello in JSON: {\"hello\":\"world\"}'})
print(r)
