import multiprocessing
import time
import traceback
import base64
import os
from typing import Optional,List
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from data_extract_util import extract_text_cache
from rag_util import (
                      split_into_sections,
                      sec_chunking
                     )
from llm_util import (check_chunking_needed,
                      first_summ,
                      summarize_final,
                      load_qa_prompt,
                      query_endpoint,
                      llm_memory
                     )


from fastapi import FastAPI, Request,File,UploadFile,Form,File

app = FastAPI(timeout=600)

headers = {"Content-Type": "application/custom+json"}
PARAMS_BASE = {'endpoint-llm': "anthropic.claude-3-sonnet-20240229-v1:0",
              'first_token_length':10000, 
              'top_p':1., 
              'temp':0.01,
              'model_name':"Claude3-sonnet",
              'second_token_length':15000,
              'chunk_len':5000,
              "persona": "Finance",
              "memory": False,
              "streaming": False
             }

class AppApiPortalRequest(BaseModel):
    app_mode: str
    file_id: Optional[str]
    original_filename: str
    enable_chat_history: int
    file_content:str
    user_input: Optional[str]

class LogDataRequest(BaseModel):
    log_data:str

FILE_CONTEXT_CACHE = None

def summarize_context(pdf_file_bytes, pdf_file_path, params):
    """
    Function for Document Summary
    
    """
    
    if pdf_file_bytes is None and pdf_file_path is None:
        return {"exception": "Please provide PDF file"}
    
    dict_words = extract_text_cache(filepath= pdf_file_path, file_bytes = pdf_file_bytes)
    
    if len(dict_words) == 0:
        return {"exception": "PDF File provided is empty"}
    
    # if len(dict_words) > 50:
    #     return {"exception": "The file is too large, will exhaust our API Call limit. Please contact AI&DS team for customized solution." }
    
    text=' '.join(dict_words.values())
    # Calculate token size of input text per model and decide chunking  
    chunking_needed = check_chunking_needed(params['model_name'].lower(), text)
    
    tokens = 0
    tic = time.time()
    
    if chunking_needed:
        params['max_len']=round(params['first_token_length'])
        sections = split_into_sections(text, params['chunk_len'])  
        num_concurrent_invocations = 10 #number of parallel calls
        pool = multiprocessing.Pool(processes=num_concurrent_invocations)
        results = pool.starmap(first_summ, [(params, section) for section in sections])
        pool.close()
        pool.join() 
        text = "##".join([x[0] for x in results])
        tokens += sum([x[1] for x in results])
        
        word_length=len(text.split())
        if word_length>max(params['chunk_len']*3,500) if "mistral" in params['model_name'].lower() else max(params['chunk_len']*3,2000): # Check if further chunking is need if text is greater than 3000 words
            sec_partial_summary=sec_chunking(word_length,text,params)
            params['max_len']=round(params['first_token_length'])
            pool = multiprocessing.Pool(processes=num_concurrent_invocations)              
            final_results = pool.starmap(first_summ, [(params, summ) for summ in sec_partial_summary]) 
            pool.close()
            pool.join()   
            #Final summary
            full_summary=[] 
            full_summary="##".join([x[0] for x in final_results])
            tokens += sum([x[1] for x in final_results])
            
            params['context']=full_summary
            params['max_len']=round(params['second_token_length'])
            summary, token_cnt=summarize_final(params)
            tokens += token_cnt
        else:
            ## Final Summary
            params['context']=text
            params['max_len']=round(params['second_token_length'])
            summary, token_cnt=summarize_final(params)
            tokens += token_cnt
    else:
        ## No Chunking Needed Summary
        params['context']=text
        params['max_len']=round(params['second_token_length'])
        summary, token_cnt=summarize_final(params)
        tokens += token_cnt
    
    toc = time.time()
    
    response = {'elapsed': round(toc-tic, 1),
                'summary': summary,
                'tokens': tokens,
                'exception': None
               }
    # container_summ.markdown(st.session_state['summary'].replace("$","USD ").replace("%", " percent"))
    return response

def chat_with_pdf(pdf_file_bytes, pdf_file_path, user_input, params):
    """
    This action takes the entire pdf as context for the following LLM actions below.
    """
    
    global FILE_CONTEXT_CACHE
    if pdf_file_bytes is None and pdf_file_path is None and FILE_CONTEXT_CACHE is None:
        raise Exception("Please provide PDF file")
    
    if pdf_file_bytes is not None:
        dict_words = extract_text_cache(filepath= pdf_file_path, file_bytes = pdf_file_bytes)
        
        if len(dict_words) == 0:
            return {"exception": "The PDF text is empty"}
        
        # if len(dict_words) > 50:
        #     return {"exception": "The file is too large, will exhaust our API Call limit. Please contact AI&DS team for customized solution." }
        
        text=' '.join(dict_words.values())
        FILE_CONTEXT_CACHE = text
    
    if user_input:
        tic = time.time()
        params['context'] = FILE_CONTEXT_CACHE
        
        ## TODO: max_len, add chunking
        params['max_len']=round(params['second_token_length'])
        
        new_user_input = None
        if params["memory"] and 'chat_memory' in params:
            new_user_input=llm_memory(user_input, params, params['chat_memory'])
            # params['question'] = new_user_input
        else:
            params['question'] = user_input
        prompt = load_qa_prompt(params)
        output_answer, tokens = query_endpoint(params,prompt)
        toc = time.time()
        
        if params["memory"]:
            chat_history={"user" :params['question'],
                          "assistant":output_answer}
            if 'chat_memory' in params:
                if isinstance(params['chat_memory'], dict):
                    params['chat_memory'] = [params['chat_memory']]
                params['chat_memory'].append(chat_history)
                
            else:
                params['chat_memory'] = [chat_history]
        
        response = {'elapsed': round(toc-tic, 1),
                    'summary': output_answer,
                    'tokens': tokens,
                    'exception': None,
                    'new_question': new_user_input,
                    'chat_memory': params['chat_memory'] if 'chat_memory' in params else None
                   }
        
        return response
@app.post("/logresponse/")
async def log_response(request: LogDataRequest):
    log_data=request.log_data
    if not log_data:
        return
    log_dir='/var/log/datascience'
    log_file_path=os.path.join(log_dir,'response.log') 
    #os.makedirs(log_dir,exist_ok=True)  

    with open(log_file_path,'a') as log_file:
            log_file.write(log_data  + "\n"+ "*" * 100 + "\n")
    return {"message": "Logging successful"}
        
@app.post("/apiportal/")
async def app_api_portal(request: AppApiPortalRequest):
    """
    app_mode: Document Summary, or Chat with PDF
    file_id: the unique identifier for file
    original_filename: the name of uploaded file
    enable_chat_history: 0 or 1
    binary_file_content: binary file io stream or None
        enable_chat_history 0, the binary file io should be not Null, indicating new file upload
        enable_chat_history 1, the binary file io would be Null, indicating continuous session
    user_input: question for the LLM
        if it's the summary mode, the user_input should be none
    """
    app_mode = request.app_mode
    file_id = request.file_id
    original_filename = request.original_filename
    enable_chat_history = request.enable_chat_history
    file_content = request.file_content
    user_input = request.user_input

    if file_content:
        binary_file_content = base64.b64decode(file_content.split(",")[1])
    else:
        binary_file_content = None

    
    global FILE_CONTEXT_CACHE
    try:
        if app_mode not in ('ChatPDF', 'Document Summary'):
            return {"exception": "APP Mode is not defined!"}
        
        if not binary_file_content and isinstance(binary_file_content, str) and len(binary_file_content) < 1:
            binary_file_content = None
        
        is_not_new_file = enable_chat_history

        if is_not_new_file == 0 and binary_file_content is None:
            return {"exception": "The uploaded file is empty"}
        
        if is_not_new_file == 0:
            FILE_CONTEXT_CACHE = None
        
        if is_not_new_file == 1 and FILE_CONTEXT_CACHE is None:
            return {"exception": "Please upload the file again. The file is lost."}
        
        if app_mode == "ChatPDF":
            if user_input is None or len(user_input) < 1:
                return {"exception": "The User input is empty"}
            if len(user_input) < 10:
                return {"exception": "Please make sure the user input is valid. We set a minimum 10 character limit."}
            
            params = PARAMS_BASE
            params['action_name'] = 'ChatPDF'
            if is_not_new_file  == 0:
                response = chat_with_pdf(binary_file_content, None, user_input, params)
            elif is_not_new_file == 1 and FILE_CONTEXT_CACHE is not None:
                response = chat_with_pdf(None, None, user_input, params)
            response['user_input'] = user_input
            return response
        
        if app_mode == 'Document Summary':
            params = PARAMS_BASE
            params['action_name'] = 'Document Summary'
            response = summarize_context(pdf_file_bytes = binary_file_content, pdf_file_path = None, params = params)
            response['user_input'] = 'summary'
            return response
    except:
        return {"exception": traceback.format_exc()}
    
    return

@app.get("/get_test/")
def get_test():  
    return JSONResponse(content="sucesses test", headers=headers)


@app.post("/test/")
async def read_root( file: UploadFile = File(...),mode: str = Form(...)):
    print(mode)
    
    return {"message": "Hello, World!"}
