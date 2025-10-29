# """
# 제품별 RAG 시스템 - 검색 결과 상세 표시 버전
# """
# import os
# import json
# import glob
# import pickle
# from typing import List, Dict, Any, Optional
# from pathlib import Path
# from collections import defaultdict

# from langchain.schema import Document
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS
# from langchain_openai import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate
# from PIL import Image
# import torch
# from transformers import CLIPProcessor, CLIPModel


# class AdvancedProductSpecificRAG:
#     """제품별 검색 RAG 시스템"""
    
#     def __init__(
#         self, 
#         data_dir: str = "../data/outputs_structured",
#         cache_dir: str = "./rag_cache_products",
#         openai_api_key: str = None,
#         use_openai: bool = True
#     ):
#         self.data_dir = data_dir
#         self.cache_dir = cache_dir
#         self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
#         self.use_openai = use_openai
        
#         os.makedirs(cache_dir, exist_ok=True)
        
#         print("텍스트 임베딩 모델 로딩 중...")
#         self.text_embeddings = HuggingFaceEmbeddings(
#             model_name="sentence-transformers/all-MiniLM-L6-v2",
#             model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'},
#             encode_kwargs={'normalize_embeddings': True}
#         )
        
#         print("이미지 임베딩 모델 로딩 중...")
#         try:
#             self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
#             self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
#         except Exception as e:
#             print(f"  경고: CLIP 모델 로딩 실패 - {e}")
#             self.clip_model = None
#             self.clip_processor = None
        
#         self.product_stores = defaultdict(dict)
        
#         self.llm = None
#         if self.use_openai and self.openai_api_key:
#             try:
#                 print("OpenAI LLM 초기화 중...")
#                 self.llm = ChatOpenAI(
#                     model="gpt-4o-mini",
#                     temperature=0.7,
#                     api_key=self.openai_api_key
#                 )
#                 print("  - OpenAI 연결 성공")
#             except Exception as e:
#                 print(f"  경고: OpenAI 초기화 실패 - {e}")
        
#         self.available_products = []
#         print("초기화 완료!\n")
    
#     def get_available_products(self) -> List[str]:
#         """사용 가능한 제품 ID 목록"""
#         product_dirs = glob.glob(os.path.join(self.data_dir, "*/"))
#         products = [Path(d).name for d in product_dirs]
#         return sorted(products)
    
#     def get_product_cache_path(self, product_id: str) -> str:
#         return os.path.join(self.cache_dir, product_id)
    
#     def save_product_store(self, product_id: str):
#         if product_id not in self.product_stores:
#             return
        
#         cache_path = self.get_product_cache_path(product_id)
#         os.makedirs(cache_path, exist_ok=True)
        
#         print(f"제품 {product_id} 저장 중...")
#         stores = self.product_stores[product_id]
        
#         if 'product' in stores:
#             stores['product'].save_local(os.path.join(cache_path, "product_store"))
#         if 'review' in stores:
#             stores['review'].save_local(os.path.join(cache_path, "review_store"))
#         if 'ocr' in stores:
#             stores['ocr'].save_local(os.path.join(cache_path, "ocr_store"))
#         if 'image' in stores:
#             with open(os.path.join(cache_path, "image_store.pkl"), 'wb') as f:
#                 pickle.dump(stores['image'], f)
        
#         print(f"  저장 완료!")
    
#     def load_product_store(self, product_id: str) -> bool:
#         cache_path = self.get_product_cache_path(product_id)
        
#         if not os.path.exists(cache_path):
#             return False
        
#         print(f"제품 {product_id} 캐시 로딩...")
#         stores = {}
        
#         try:
#             product_path = os.path.join(cache_path, "product_store")
#             if os.path.exists(product_path):
#                 stores['product'] = FAISS.load_local(
#                     product_path, self.text_embeddings, allow_dangerous_deserialization=True
#                 )
            
#             review_path = os.path.join(cache_path, "review_store")
#             if os.path.exists(review_path):
#                 stores['review'] = FAISS.load_local(
#                     review_path, self.text_embeddings, allow_dangerous_deserialization=True
#                 )
            
#             ocr_path = os.path.join(cache_path, "ocr_store")
#             if os.path.exists(ocr_path):
#                 stores['ocr'] = FAISS.load_local(
#                     ocr_path, self.text_embeddings, allow_dangerous_deserialization=True
#                 )
            
#             image_path = os.path.join(cache_path, "image_store.pkl")
#             if os.path.exists(image_path):
#                 with open(image_path, 'rb') as f:
#                     stores['image'] = pickle.load(f)
            
#             self.product_stores[product_id] = stores
#             print(f"  로드 완료!")
#             return True
#         except Exception as e:
#             print(f"  로드 실패: {e}")
#             return False
    
#     def load_product_chunks(self, product_id: str) -> List[Document]:
#         documents = []
#         product_file = os.path.join(self.data_dir, product_id, f"product_{product_id}.json")
        
#         if not os.path.exists(product_file):
#             print(f"        ⚠️  파일 없음: {product_file}")
#             return documents
        
#         with open(product_file, 'r', encoding='utf-8') as f:
#             try:
#                 data = json.load(f)  # 간단하게 직접 로드
#             except json.JSONDecodeError as e:
#                 print(f"        ❌ JSON 파싱 에러: {e}")
#                 return documents
#             except Exception as e:
#                 print(f"        ❌ 파일 읽기 에러: {e}")
#                 return documents
            
#             # Chunk 1: 기본 정보 (자연어로 변환)
#             basic_text = f"상품명: {data.get('productTitle', 'N/A')}"
#             if data.get('brand'):
#                 basic_text += f"\n브랜드: {data.get('brand')}"
#             basic_text += f"\n상품ID: {data.get('productId')}"
            
#             documents.append(Document(
#                 page_content=basic_text,
#                 metadata={"type": "product", "product_id": product_id, "chunk_type": "basic"}
#             ))
            
#             # Chunk 2: 가격 정보 (자연어로 변환)
#             price_text = f"가격: {data.get('price', 0)}원"
#             if data.get('unitPrice'):
#                 price_text += f"\n개당 가격: {data.get('unitPrice')}원"
#             if data.get('unitPriceDescription'):
#                 price_text += f"\n{data.get('unitPriceDescription')}"
            
#             documents.append(Document(
#                 page_content=price_text,
#                 metadata={"type": "product", "product_id": product_id, "chunk_type": "price"}
#             ))
            
#             # Chunk 3: 배송 정보 (자연어로 변환)
#             if data.get('delivery'):
#                 delivery = data['delivery']
#                 delivery_text_parts = []
                
#                 if delivery.get('descriptions'):
#                     # HTML 태그 제거
#                     import re
#                     desc = re.sub(r'<[^>]+>', ' ', str(delivery.get('descriptions', '')))
#                     delivery_text_parts.append(f"배송: {desc}")
                
#                 if delivery.get('type'):
#                     delivery_text_parts.append(f"배송 타입: {delivery.get('type')}")
                
#                 if delivery.get('speedType'):
#                     delivery_text_parts.append(f"배송 속도: {delivery.get('speedType')}")
                
#                 if delivery_text_parts:
#                     documents.append(Document(
#                         page_content="\n".join(delivery_text_parts),
#                         metadata={"type": "product", "product_id": product_id, "chunk_type": "delivery"}
#                     ))
            
#             # Chunk 4: 옵션 정보 (자연어로 변환)
#             if data.get('options'):
#                 options_text_parts = ["구매 옵션:"]
#                 for opt in data['options'][:5]:  # 최대 5개만
#                     opt_name = opt.get('optionItemName', 'N/A')
#                     opt_price = opt.get('finalPrice', 'N/A')
#                     options_text_parts.append(f"- {opt_name}: {opt_price}")
                
#                 documents.append(Document(
#                     page_content="\n".join(options_text_parts),
#                     metadata={"type": "product", "product_id": product_id, "chunk_type": "options"}
#                 ))
            
#             # Chunk 5: 캐시백 정보 (자연어로 변환)
#             if data.get('cashBackSummary', {}).get('basicCashBackList'):
#                 cashback_list = data['cashBackSummary']['basicCashBackList']
#                 cashback_text_parts = ["캐시백 혜택:"]
#                 for cb in cashback_list:
#                     benefit = cb.get('benefit', 'N/A')
#                     amount = cb.get('amount', 0)
#                     cashback_text_parts.append(f"- {benefit}: {amount}원")
                
#                 documents.append(Document(
#                     page_content="\n".join(cashback_text_parts),
#                     metadata={"type": "product", "product_id": product_id, "chunk_type": "cashback"}
#                 ))
        
#         print(f"        ✓ {len(documents)}개 product chunk 생성")
#         return documents
    
#     def load_review_chunks(self, product_id: str) -> List[Document]:
#         documents = []
#         review_files = glob.glob(os.path.join(self.data_dir, product_id, f"reviews_*.jsonl"))
        
#         for file_path in review_files:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 for line in f:
#                     try:
#                         review = json.loads(line.strip())
#                         if review.get('content'):
#                             documents.append(Document(
#                                 page_content=review['content'],
#                                 metadata={
#                                     "type": "review",
#                                     "product_id": product_id,
#                                     "rating": review.get('rating')
#                                 }
#                             ))
#                     except:
#                         continue
        
#         return documents
    
#     def load_ocr_chunks(self, product_id: str) -> List[Document]:
#         documents = []
#         ocr_file = os.path.join(self.data_dir, product_id, f"ocrs_{product_id}.json")
        
#         if not os.path.exists(ocr_file):
#             return documents
        
#         with open(ocr_file, 'r', encoding='utf-8') as f:
#             try:
#                 for item in json.load(f):
#                     if item.get('ocr_text'):
#                         documents.append(Document(
#                             page_content=item['ocr_text'],
#                             metadata={"type": "ocr", "product_id": product_id}
#                         ))
#             except:
#                 pass
        
#         return documents
    
#     def load_image_chunks(self, product_id: str) -> List[Dict[str, Any]]:
#         if not self.clip_model or not self.clip_processor:
#             return []
        
#         image_data = []
#         image_dir = os.path.join(self.data_dir, product_id, "images")
        
#         if not os.path.exists(image_dir):
#             return image_data
        
#         image_files = glob.glob(os.path.join(image_dir, "*.[pj][np]g")) + \
#                      glob.glob(os.path.join(image_dir, "*.png"))
        
#         for image_path in image_files:
#             try:
#                 image = Image.open(image_path).convert('RGB')
#                 inputs = self.clip_processor(images=image, return_tensors="pt")
                
#                 with torch.no_grad():
#                     image_features = self.clip_model.get_image_features(**inputs)
#                     image_embedding = image_features.squeeze().numpy()
                
#                 image_data.append({
#                     "path": image_path,
#                     "embedding": image_embedding,
#                     "metadata": {"type": "image", "product_id": product_id}
#                 })
#             except:
#                 continue
        
#         return image_data
    
#     def build_product_store(self, product_id: str, force_rebuild: bool = False):
#         if not force_rebuild and self.load_product_store(product_id):
#             print(f"제품 {product_id}: 캐시 사용\n")
#             return
        
#         print(f"\n=== 제품 {product_id} 구축 중 ===")
#         stores = {}
        
#         print("  [1/4] Product 데이터 로딩...")
#         product_docs = self.load_product_chunks(product_id)
#         if product_docs:
#             stores['product'] = FAISS.from_documents(product_docs, self.text_embeddings)
#             print(f"        ✓ {len(product_docs)}개 chunk")
        
#         print("  [2/4] Review 데이터 로딩...")
#         review_docs = self.load_review_chunks(product_id)
#         if review_docs:
#             stores['review'] = FAISS.from_documents(review_docs, self.text_embeddings)
#             print(f"        ✓ {len(review_docs)}개 chunk")
        
#         print("  [3/4] OCR 데이터 로딩...")
#         ocr_docs = self.load_ocr_chunks(product_id)
#         if ocr_docs:
#             stores['ocr'] = FAISS.from_documents(ocr_docs, self.text_embeddings)
#             print(f"        ✓ {len(ocr_docs)}개 chunk")
        
#         print("  [4/4] Image 데이터 로딩...")
#         image_data = self.load_image_chunks(product_id)
#         if image_data:
#             import faiss
#             import numpy as np
            
#             embeddings = np.array([item['embedding'] for item in image_data]).astype('float32')
#             index = faiss.IndexFlatL2(embeddings.shape[1])
#             index.add(embeddings)
#             stores['image'] = {'index': index, 'data': image_data}
#             print(f"        ✓ {len(image_data)}개 이미지")
        
#         self.product_stores[product_id] = stores
#         self.save_product_store(product_id)
#         print(f"=== 구축 완료 ===\n")
    
#     def retrieve(self, product_id: str, query: str) -> Dict[str, List]:
#         if product_id not in self.product_stores:
#             raise ValueError(f"제품 {product_id} 스토어 없음")
        
#         results = {"products": [], "reviews": [], "ocrs": [], "images": []}
#         stores = self.product_stores[product_id]
        
#         if 'product' in stores:
#             results["products"] = [
#                 {"content": doc.page_content, "metadata": doc.metadata, "score": score}
#                 for doc, score in stores['product'].similarity_search_with_score(query, k=3)
#             ]
        
#         if 'review' in stores:
#             results["reviews"] = [
#                 {"content": doc.page_content, "metadata": doc.metadata, "score": score}
#                 for doc, score in stores['review'].similarity_search_with_score(query, k=3)
#             ]
        
#         if 'ocr' in stores:
#             results["ocrs"] = [
#                 {"content": doc.page_content, "metadata": doc.metadata, "score": score}
#                 for doc, score in stores['ocr'].similarity_search_with_score(query, k=3)
#             ]
        
#         if 'image' in stores and self.clip_model and self.clip_processor:
#             try:
#                 inputs = self.clip_processor(text=query, return_tensors="pt", padding=True)
#                 with torch.no_grad():
#                     text_features = self.clip_model.get_text_features(**inputs)
#                     query_embedding = text_features.squeeze().numpy().astype('float32').reshape(1, -1)
                
#                 distances, indices = stores['image']['index'].search(query_embedding, 3)
                
#                 for idx, distance in zip(indices[0], distances[0]):
#                     if idx < len(stores['image']['data']):
#                         item = stores['image']['data'][idx]
#                         results["images"].append({
#                             "path": item['path'],
#                             "metadata": item['metadata'],
#                             "score": float(distance)
#                         })
#             except:
#                 pass
        
#         return results
    
#     def print_retrieval_results(self, retrieved_docs: Dict[str, List], verbose: bool = True):
#         """검색 결과 출력"""
#         print("\n" + "="*80)
#         print("검색 결과 상세")
#         print("="*80)
        
#         # Products
#         if retrieved_docs["products"]:
#             print(f"\n📦 상품 정보 ({len(retrieved_docs['products'])}개)")
#             print("-"*80)
#             for i, doc in enumerate(retrieved_docs["products"], 1):
#                 print(f"\n[{i}] Score: {doc['score']:.4f}")
#                 print(f"Type: {doc['metadata'].get('chunk_type', 'unknown')}")
#                 if verbose:
#                     try:
#                         content = json.loads(doc['content'])
#                         print(f"Content:")
#                         print(json.dumps(content, ensure_ascii=False, indent=2))
#                     except:
#                         print(f"Content: {doc['content'][:200]}...")
#                 else:
#                     print(f"Content: {doc['content'][:100]}...")
        
#         # Reviews
#         if retrieved_docs["reviews"]:
#             print(f"\n⭐ 리뷰 ({len(retrieved_docs['reviews'])}개)")
#             print("-"*80)
#             for i, doc in enumerate(retrieved_docs["reviews"], 1):
#                 print(f"\n[{i}] Score: {doc['score']:.4f}")
#                 print(f"Rating: {doc['metadata'].get('rating', 'N/A')}점")
#                 if verbose:
#                     print(f"Content:\n{doc['content'][:500]}...")
#                 else:
#                     print(f"Content: {doc['content'][:150]}...")
        
#         # OCR
#         if retrieved_docs["ocrs"]:
#             print(f"\n🔍 OCR 텍스트 ({len(retrieved_docs['ocrs'])}개)")
#             print("-"*80)
#             for i, doc in enumerate(retrieved_docs["ocrs"], 1):
#                 print(f"\n[{i}] Score: {doc['score']:.4f}")
#                 print(f"Content: {doc['content']}")
        
#         # Images
#         if retrieved_docs["images"]:
#             print(f"\n🖼️  이미지 ({len(retrieved_docs['images'])}개)")
#             print("-"*80)
#             for i, img in enumerate(retrieved_docs["images"], 1):
#                 print(f"\n[{i}] Score: {img['score']:.4f}")
#                 print(f"Path: {img['path']}")
        
#         print("\n" + "="*80)
    
#     def generate_answer(self, query: str, retrieved_docs: Dict, product_id: str) -> str:
#         if not self.llm:
#             return "OpenAI 미사용 모드 (검색 결과만 확인)"
        
#         context_parts = []
        
#         if retrieved_docs["products"]:
#             context_parts.append("=== 상품 정보 ===")
#             for doc in retrieved_docs["products"]:
#                 context_parts.append(doc["content"])
        
#         if retrieved_docs["reviews"]:
#             context_parts.append("\n=== 리뷰 ===")
#             for doc in retrieved_docs["reviews"][:3]:
#                 context_parts.append(doc["content"][:400])
        
#         if retrieved_docs["ocrs"]:
#             context_parts.append("\n=== OCR ===")
#             for doc in retrieved_docs["ocrs"]:
#                 context_parts.append(doc["content"])
        
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", "당신은 쇼핑몰 상품 Q&A 어시스턴트입니다."),
#             ("user", "제품 {product_id}\n\n{context}\n\n질문: {query}")
#         ])
        
#         messages = prompt.format_messages(
#             context="\n".join(context_parts), 
#             query=query, 
#             product_id=product_id
#         )
#         response = self.llm.invoke(messages)
#         return response.content
    
#     def query(self, product_id: str, user_query: str, show_retrieval: bool = False, verbose: bool = False) -> Dict[str, Any]:
#         """전체 파이프라인"""
#         print(f"\n질문: {user_query}")
#         print(f"제품: {product_id}\n")
        
#         retrieved = self.retrieve(product_id, user_query)
        
#         print(f"검색 완료:")
#         print(f"  - 상품: {len(retrieved['products'])}개")
#         print(f"  - 리뷰: {len(retrieved['reviews'])}개")
#         print(f"  - OCR: {len(retrieved['ocrs'])}개")
#         print(f"  - 이미지: {len(retrieved['images'])}개")
        
#         # 검색 결과 상세 출력
#         if show_retrieval:
#             self.print_retrieval_results(retrieved, verbose=verbose)
        
#         answer = self.generate_answer(user_query, retrieved, product_id)
        
#         return {
#             "product_id": product_id,
#             "query": user_query,
#             "answer": answer,
#             "retrieved_docs": retrieved
#         }


# def main():
#     import argparse
#     from dotenv import load_dotenv
    
#     load_dotenv()
    
#     parser = argparse.ArgumentParser(description='Product RAG System')
#     parser.add_argument('--data-dir', type=str, default='../data/outputs_structured')
#     parser.add_argument('--cache-dir', type=str, default='./rag_cache_products')
#     parser.add_argument('--build', action='store_true')
#     parser.add_argument('--force-rebuild', action='store_true')
#     parser.add_argument('--product-id', type=str)
#     parser.add_argument('--query', type=str)
#     parser.add_argument('--list-products', action='store_true')
#     parser.add_argument('--no-openai', action='store_true')
#     parser.add_argument('--show-retrieval', action='store_true', help='검색 결과 상세 표시')
#     parser.add_argument('--verbose', action='store_true', help='더 자세한 출력')
    
#     args = parser.parse_args()
    
#     rag = AdvancedProductSpecificRAG(
#         data_dir=args.data_dir,
#         cache_dir=args.cache_dir,
#         use_openai=not args.no_openai
#     )
    
#     if args.list_products:
#         products = rag.get_available_products()
#         print(f"\n사용 가능한 제품 ({len(products)}개):")
#         for p in products:
#             print(f"  - {p}")
#         print()
#         return
    
#     if args.build:
#         if args.product_id:
#             rag.build_product_store(args.product_id, args.force_rebuild)
#         else:
#             products = rag.get_available_products()
#             for pid in products:
#                 rag.build_product_store(pid, args.force_rebuild)
#         return
    
#     if args.query and args.product_id:
#         if args.product_id not in rag.product_stores:
#             print("벡터 스토어 구축 중...\n")
#             rag.build_product_store(args.product_id)
        
#         result = rag.query(
#             args.product_id, 
#             args.query, 
#             show_retrieval=args.show_retrieval,
#             verbose=args.verbose
#         )
        
#         print("\n" + "="*80)
#         print("답변:")
#         print("="*80)
#         print(result["answer"])
#         print("="*80)
#         return
    
#     # 대화형 모드
#     if args.product_id:
#         product_id = args.product_id
#     else:
#         products = rag.get_available_products()
#         print(f"\n사용 가능한 제품: {products}")
#         product_id = input("제품 ID 입력: ").strip()
    
#     if product_id not in rag.product_stores:
#         rag.build_product_store(product_id)
    
#     print(f"\n{'='*80}")
#     print(f"제품 {product_id} 대화형 모드")
#     print(f"명령어: 'detail' - 검색 결과 상세, 'verbose' - 더 자세히")
#     print(f"{'='*80}\n")
    
#     show_detail = args.show_retrieval
#     verbose_mode = args.verbose
    
#     while True:
#         try:
#             user_input = input("\n질문: ").strip()
            
#             if user_input.lower() in ['exit', 'quit', '종료']:
#                 break
#             elif user_input.lower() == 'detail':
#                 show_detail = not show_detail
#                 print(f"검색 결과 상세 표시: {'ON' if show_detail else 'OFF'}")
#                 continue
#             elif user_input.lower() == 'verbose':
#                 verbose_mode = not verbose_mode
#                 print(f"Verbose 모드: {'ON' if verbose_mode else 'OFF'}")
#                 continue
            
#             if user_input:
#                 result = rag.query(product_id, user_input, show_retrieval=show_detail, verbose=verbose_mode)
#                 print("\n" + "="*80)
#                 print(result["answer"])
#                 print("="*80)
#         except KeyboardInterrupt:
#             break


# if __name__ == "__main__":
#     main()

"""
제품별 RAG 시스템 - 검색 결과 상세 표시 버전
"""
import os
import json
import glob
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict

from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel


class AdvancedProductSpecificRAG:
    """제품별 검색 RAG 시스템"""
    
    def __init__(
        self, 
        data_dir: str = "../data/outputs_structured",
        cache_dir: str = "./rag_cache_products",
        openai_api_key: str = None,
        use_openai: bool = True
    ):
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.use_openai = use_openai
        
        os.makedirs(cache_dir, exist_ok=True)
        
        print("텍스트 임베딩 모델 로딩 중...")
        self.text_embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        print("이미지 임베딩 모델 로딩 중...")
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except Exception as e:
            print(f"  경고: CLIP 모델 로딩 실패 - {e}")
            self.clip_model = None
            self.clip_processor = None
        
        self.product_stores = defaultdict(dict)
        
        self.llm = None
        if self.use_openai and self.openai_api_key:
            try:
                print("OpenAI LLM 초기화 중...")
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=self.openai_api_key
                )
                print("  - OpenAI 연결 성공")
            except Exception as e:
                print(f"  경고: OpenAI 초기화 실패 - {e}")
        
        self.available_products = []
        print("초기화 완료!\n")
    
    def get_available_products(self) -> List[str]:
        """사용 가능한 제품 ID 목록"""
        product_dirs = glob.glob(os.path.join(self.data_dir, "*/"))
        products = [Path(d).name for d in product_dirs]
        return sorted(products)
    
    def get_product_cache_path(self, product_id: str) -> str:
        return os.path.join(self.cache_dir, product_id)
    
    def save_product_store(self, product_id: str):
        if product_id not in self.product_stores:
            return
        
        cache_path = self.get_product_cache_path(product_id)
        os.makedirs(cache_path, exist_ok=True)
        
        print(f"제품 {product_id} 저장 중...")
        stores = self.product_stores[product_id]
        
        if 'product' in stores:
            stores['product'].save_local(os.path.join(cache_path, "product_store"))
        if 'review' in stores:
            stores['review'].save_local(os.path.join(cache_path, "review_store"))
        if 'ocr' in stores:
            stores['ocr'].save_local(os.path.join(cache_path, "ocr_store"))
        if 'image' in stores:
            with open(os.path.join(cache_path, "image_store.pkl"), 'wb') as f:
                pickle.dump(stores['image'], f)
        
        print(f"  저장 완료!")
    
    def load_product_store(self, product_id: str) -> bool:
        cache_path = self.get_product_cache_path(product_id)
        
        if not os.path.exists(cache_path):
            return False
        
        print(f"제품 {product_id} 캐시 로딩...")
        stores = {}
        
        try:
            product_path = os.path.join(cache_path, "product_store")
            if os.path.exists(product_path):
                stores['product'] = FAISS.load_local(
                    product_path, self.text_embeddings, allow_dangerous_deserialization=True
                )
            
            review_path = os.path.join(cache_path, "review_store")
            if os.path.exists(review_path):
                stores['review'] = FAISS.load_local(
                    review_path, self.text_embeddings, allow_dangerous_deserialization=True
                )
            
            ocr_path = os.path.join(cache_path, "ocr_store")
            if os.path.exists(ocr_path):
                stores['ocr'] = FAISS.load_local(
                    ocr_path, self.text_embeddings, allow_dangerous_deserialization=True
                )
            
            image_path = os.path.join(cache_path, "image_store.pkl")
            if os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    stores['image'] = pickle.load(f)
            
            self.product_stores[product_id] = stores
            print(f"  로드 완료!")
            return True
        except Exception as e:
            print(f"  로드 실패: {e}")
            return False
    
    def load_product_chunks(self, product_id: str) -> List[Document]:
        documents = []
        product_file = os.path.join(self.data_dir, product_id, f"product_{product_id}.json")
        
        if not os.path.exists(product_file):
            print(f"        ⚠️  파일 없음: {product_file}")
            return documents
        
        with open(product_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)  # 간단하게 직접 로드
            except json.JSONDecodeError as e:
                print(f"        ❌ JSON 파싱 에러: {e}")
                return documents
            except Exception as e:
                print(f"        ❌ 파일 읽기 에러: {e}")
                return documents
            
            # Chunk 1: 기본 정보 (자연어로 변환)
            basic_text = f"상품명: {data.get('productTitle', 'N/A')}"
            if data.get('brand'):
                basic_text += f"\n브랜드: {data.get('brand')}"
            basic_text += f"\n상품ID: {data.get('productId')}"
            
            documents.append(Document(
                page_content=basic_text,
                metadata={"type": "product", "product_id": product_id, "chunk_type": "basic"}
            ))
            
            # Chunk 2: 가격 정보 (자연어로 변환)
            price_text = f"가격: {data.get('price', 0)}원"
            if data.get('unitPrice'):
                price_text += f"\n개당 가격: {data.get('unitPrice')}원"
            if data.get('unitPriceDescription'):
                price_text += f"\n{data.get('unitPriceDescription')}"
            
            documents.append(Document(
                page_content=price_text,
                metadata={"type": "product", "product_id": product_id, "chunk_type": "price"}
            ))
            
            # Chunk 3: 배송 정보 (자연어로 변환)
            if data.get('delivery'):
                delivery = data['delivery']
                delivery_text_parts = []
                
                if delivery.get('descriptions'):
                    # HTML 태그 제거
                    import re
                    desc = re.sub(r'<[^>]+>', ' ', str(delivery.get('descriptions', '')))
                    delivery_text_parts.append(f"배송: {desc}")
                
                if delivery.get('type'):
                    delivery_text_parts.append(f"배송 타입: {delivery.get('type')}")
                
                if delivery.get('speedType'):
                    delivery_text_parts.append(f"배송 속도: {delivery.get('speedType')}")
                
                if delivery_text_parts:
                    documents.append(Document(
                        page_content="\n".join(delivery_text_parts),
                        metadata={"type": "product", "product_id": product_id, "chunk_type": "delivery"}
                    ))
            
            # Chunk 4: 옵션 정보 (자연어로 변환)
            if data.get('options'):
                options_text_parts = ["구매 옵션:"]
                for opt in data['options'][:5]:  # 최대 5개만
                    opt_name = opt.get('optionItemName', 'N/A')
                    opt_price = opt.get('finalPrice', 'N/A')
                    options_text_parts.append(f"- {opt_name}: {opt_price}")
                
                documents.append(Document(
                    page_content="\n".join(options_text_parts),
                    metadata={"type": "product", "product_id": product_id, "chunk_type": "options"}
                ))
            
            # Chunk 5: 캐시백 정보 (자연어로 변환)
            if data.get('cashBackSummary', {}).get('basicCashBackList'):
                cashback_list = data['cashBackSummary']['basicCashBackList']
                cashback_text_parts = ["캐시백 혜택:"]
                for cb in cashback_list:
                    benefit = cb.get('benefit', 'N/A')
                    amount = cb.get('amount', 0)
                    cashback_text_parts.append(f"- {benefit}: {amount}원")
                
                documents.append(Document(
                    page_content="\n".join(cashback_text_parts),
                    metadata={"type": "product", "product_id": product_id, "chunk_type": "cashback"}
                ))
            
            # Chunk 6+: 상품 문의 (각 문의+답변을 하나의 청크로)
            if data.get('inquiries'):
                for idx, inquiry in enumerate(data['inquiries']):
                    # 고객 질문
                    question = inquiry.get('content', '').strip()
                    if not question:
                        continue
                    
                    # 판매자 답변들 (comments 배열)
                    answers = []
                    if inquiry.get('comments'):
                        for comment in inquiry['comments']:
                            answer_text = comment.get('content', '').strip()
                            if answer_text:
                                answers.append(answer_text)
                    
                    # QA 텍스트 생성
                    if answers:
                        # 답변이 있는 경우
                        qa_text = f"고객 문의: {question}\n\n판매자 답변: {answers[0]}"
                        # 답변이 여러 개면 첫 번째만 사용
                    else:
                        # 답변이 없는 경우 (질문만)
                        qa_text = f"고객 문의: {question}\n\n판매자 답변: (답변 대기 중)"
                    
                    documents.append(Document(
                        page_content=qa_text,
                        metadata={
                            "type": "product",
                            "product_id": product_id,
                            "chunk_type": f"inquiry_{idx}",
                            "inquiry_id": inquiry.get('inquiryId'),
                            "has_answer": len(answers) > 0
                        }
                    ))
        
        print(f"        ✓ {len(documents)}개 product chunk 생성")
        return documents
    
    def load_review_chunks(self, product_id: str) -> List[Document]:
        documents = []
        review_files = glob.glob(os.path.join(self.data_dir, product_id, f"reviews_*.jsonl"))
        
        for file_path in review_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        review = json.loads(line.strip())
                        if review.get('content'):
                            documents.append(Document(
                                page_content=review['content'],
                                metadata={
                                    "type": "review",
                                    "product_id": product_id,
                                    "rating": review.get('rating')
                                }
                            ))
                    except:
                        continue
        
        return documents
    
    def load_ocr_chunks(self, product_id: str) -> List[Document]:
        documents = []
        ocr_file = os.path.join(self.data_dir, product_id, f"ocrs_{product_id}.json")
        
        if not os.path.exists(ocr_file):
            return documents
        
        with open(ocr_file, 'r', encoding='utf-8') as f:
            try:
                for item in json.load(f):
                    if item.get('ocr_text'):
                        documents.append(Document(
                            page_content=item['ocr_text'],
                            metadata={"type": "ocr", "product_id": product_id}
                        ))
            except:
                pass
        
        return documents
    
    def load_image_chunks(self, product_id: str) -> List[Dict[str, Any]]:
        if not self.clip_model or not self.clip_processor:
            return []
        
        image_data = []
        image_dir = os.path.join(self.data_dir, product_id, "images")
        
        if not os.path.exists(image_dir):
            return image_data
        
        image_files = glob.glob(os.path.join(image_dir, "*.[pj][np]g")) + \
                     glob.glob(os.path.join(image_dir, "*.png"))
        
        for image_path in image_files:
            try:
                image = Image.open(image_path).convert('RGB')
                inputs = self.clip_processor(images=image, return_tensors="pt")
                
                with torch.no_grad():
                    image_features = self.clip_model.get_image_features(**inputs)
                    image_embedding = image_features.squeeze().numpy()
                
                image_data.append({
                    "path": image_path,
                    "embedding": image_embedding,
                    "metadata": {"type": "image", "product_id": product_id}
                })
            except:
                continue
        
        return image_data
    
    def build_product_store(self, product_id: str, force_rebuild: bool = False):
        if not force_rebuild and self.load_product_store(product_id):
            print(f"제품 {product_id}: 캐시 사용\n")
            return
        
        print(f"\n=== 제품 {product_id} 구축 중 ===")
        stores = {}
        
        print("  [1/4] Product 데이터 로딩...")
        product_docs = self.load_product_chunks(product_id)
        if product_docs:
            stores['product'] = FAISS.from_documents(product_docs, self.text_embeddings)
            print(f"        ✓ {len(product_docs)}개 chunk")
        
        print("  [2/4] Review 데이터 로딩...")
        review_docs = self.load_review_chunks(product_id)
        if review_docs:
            stores['review'] = FAISS.from_documents(review_docs, self.text_embeddings)
            print(f"        ✓ {len(review_docs)}개 chunk")
        
        print("  [3/4] OCR 데이터 로딩...")
        ocr_docs = self.load_ocr_chunks(product_id)
        if ocr_docs:
            stores['ocr'] = FAISS.from_documents(ocr_docs, self.text_embeddings)
            print(f"        ✓ {len(ocr_docs)}개 chunk")
        
        print("  [4/4] Image 데이터 로딩...")
        image_data = self.load_image_chunks(product_id)
        if image_data:
            import faiss
            import numpy as np
            
            embeddings = np.array([item['embedding'] for item in image_data]).astype('float32')
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            stores['image'] = {'index': index, 'data': image_data}
            print(f"        ✓ {len(image_data)}개 이미지")
        
        self.product_stores[product_id] = stores
        self.save_product_store(product_id)
        print(f"=== 구축 완료 ===\n")
    
    def retrieve(self, product_id: str, query: str) -> Dict[str, List]:
        if product_id not in self.product_stores:
            raise ValueError(f"제품 {product_id} 스토어 없음")
        
        results = {"products": [], "reviews": [], "ocrs": [], "images": []}
        stores = self.product_stores[product_id]
        
        if 'product' in stores:
            results["products"] = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": score}
                for doc, score in stores['product'].similarity_search_with_score(query, k=3)
            ]
        
        if 'review' in stores:
            results["reviews"] = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": score}
                for doc, score in stores['review'].similarity_search_with_score(query, k=3)
            ]
        
        if 'ocr' in stores:
            results["ocrs"] = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": score}
                for doc, score in stores['ocr'].similarity_search_with_score(query, k=3)
            ]
        
        if 'image' in stores and self.clip_model and self.clip_processor:
            try:
                inputs = self.clip_processor(text=query, return_tensors="pt", padding=True)
                with torch.no_grad():
                    text_features = self.clip_model.get_text_features(**inputs)
                    query_embedding = text_features.squeeze().numpy().astype('float32').reshape(1, -1)
                
                distances, indices = stores['image']['index'].search(query_embedding, 3)
                
                for idx, distance in zip(indices[0], distances[0]):
                    if idx < len(stores['image']['data']):
                        item = stores['image']['data'][idx]
                        results["images"].append({
                            "path": item['path'],
                            "metadata": item['metadata'],
                            "score": float(distance)
                        })
            except:
                pass
        
        return results
    
    def print_retrieval_results(self, retrieved_docs: Dict[str, List], verbose: bool = True):
        """검색 결과 출력"""
        print("\n" + "="*80)
        print("검색 결과 상세")
        print("="*80)
        
        # Products
        if retrieved_docs["products"]:
            print(f"\n📦 상품 정보 ({len(retrieved_docs['products'])}개)")
            print("-"*80)
            for i, doc in enumerate(retrieved_docs["products"], 1):
                print(f"\n[{i}] Score: {doc['score']:.4f}")
                print(f"Type: {doc['metadata'].get('chunk_type', 'unknown')}")
                if verbose:
                    try:
                        content = json.loads(doc['content'])
                        print(f"Content:")
                        print(json.dumps(content, ensure_ascii=False, indent=2))
                    except:
                        print(f"Content: {doc['content'][:200]}...")
                else:
                    print(f"Content: {doc['content'][:100]}...")
        
        # Reviews
        if retrieved_docs["reviews"]:
            print(f"\n⭐ 리뷰 ({len(retrieved_docs['reviews'])}개)")
            print("-"*80)
            for i, doc in enumerate(retrieved_docs["reviews"], 1):
                print(f"\n[{i}] Score: {doc['score']:.4f}")
                print(f"Rating: {doc['metadata'].get('rating', 'N/A')}점")
                if verbose:
                    print(f"Content:\n{doc['content'][:500]}...")
                else:
                    print(f"Content: {doc['content'][:150]}...")
        
        # OCR
        if retrieved_docs["ocrs"]:
            print(f"\n🔍 OCR 텍스트 ({len(retrieved_docs['ocrs'])}개)")
            print("-"*80)
            for i, doc in enumerate(retrieved_docs["ocrs"], 1):
                print(f"\n[{i}] Score: {doc['score']:.4f}")
                print(f"Content: {doc['content']}")
        
        # Images
        if retrieved_docs["images"]:
            print(f"\n🖼️  이미지 ({len(retrieved_docs['images'])}개)")
            print("-"*80)
            for i, img in enumerate(retrieved_docs["images"], 1):
                print(f"\n[{i}] Score: {img['score']:.4f}")
                print(f"Path: {img['path']}")
        
        print("\n" + "="*80)
    
    def generate_answer(self, query: str, retrieved_docs: Dict, product_id: str) -> str:
        if not self.llm:
            return "OpenAI 미사용 모드 (검색 결과만 확인)"
        
        context_parts = []
        
        if retrieved_docs["products"]:
            context_parts.append("=== 상품 정보 ===")
            for doc in retrieved_docs["products"]:
                context_parts.append(doc["content"])
        
        if retrieved_docs["reviews"]:
            context_parts.append("\n=== 리뷰 ===")
            for doc in retrieved_docs["reviews"][:3]:
                context_parts.append(doc["content"][:400])
        
        if retrieved_docs["ocrs"]:
            context_parts.append("\n=== OCR ===")
            for doc in retrieved_docs["ocrs"]:
                context_parts.append(doc["content"])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 쇼핑몰 상품 Q&A 어시스턴트입니다."),
            ("user", "제품 {product_id}\n\n{context}\n\n질문: {query}")
        ])
        
        messages = prompt.format_messages(
            context="\n".join(context_parts), 
            query=query, 
            product_id=product_id
        )
        response = self.llm.invoke(messages)
        return response.content
    
    def query(self, product_id: str, user_query: str, show_retrieval: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """전체 파이프라인"""
        print(f"\n질문: {user_query}")
        print(f"제품: {product_id}\n")
        
        retrieved = self.retrieve(product_id, user_query)
        
        print(f"검색 완료:")
        print(f"  - 상품: {len(retrieved['products'])}개")
        print(f"  - 리뷰: {len(retrieved['reviews'])}개")
        print(f"  - OCR: {len(retrieved['ocrs'])}개")
        print(f"  - 이미지: {len(retrieved['images'])}개")
        
        # 검색 결과 상세 출력
        if show_retrieval:
            self.print_retrieval_results(retrieved, verbose=verbose)
        
        answer = self.generate_answer(user_query, retrieved, product_id)
        
        return {
            "product_id": product_id,
            "query": user_query,
            "answer": answer,
            "retrieved_docs": retrieved
        }


def main():
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Product RAG System')
    parser.add_argument('--data-dir', type=str, default='../data/outputs_structured')
    parser.add_argument('--cache-dir', type=str, default='./rag_cache_products')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--force-rebuild', action='store_true')
    parser.add_argument('--product-id', type=str)
    parser.add_argument('--query', type=str)
    parser.add_argument('--list-products', action='store_true')
    parser.add_argument('--no-openai', action='store_true')
    parser.add_argument('--show-retrieval', action='store_true', help='검색 결과 상세 표시')
    parser.add_argument('--verbose', action='store_true', help='더 자세한 출력')
    
    args = parser.parse_args()
    
    rag = AdvancedProductSpecificRAG(
        data_dir=args.data_dir,
        cache_dir=args.cache_dir,
        use_openai=not args.no_openai
    )
    
    if args.list_products:
        products = rag.get_available_products()
        print(f"\n사용 가능한 제품 ({len(products)}개):")
        for p in products:
            print(f"  - {p}")
        print()
        return
    
    if args.build:
        if args.product_id:
            rag.build_product_store(args.product_id, args.force_rebuild)
        else:
            products = rag.get_available_products()
            for pid in products:
                rag.build_product_store(pid, args.force_rebuild)
        return
    
    if args.query and args.product_id:
        if args.product_id not in rag.product_stores:
            print("벡터 스토어 구축 중...\n")
            rag.build_product_store(args.product_id)
        
        result = rag.query(
            args.product_id, 
            args.query, 
            show_retrieval=args.show_retrieval,
            verbose=args.verbose
        )
        
        print("\n" + "="*80)
        print("답변:")
        print("="*80)
        print(result["answer"])
        print("="*80)
        return
    
    # 대화형 모드
    if args.product_id:
        product_id = args.product_id
    else:
        products = rag.get_available_products()
        print(f"\n사용 가능한 제품: {products}")
        product_id = input("제품 ID 입력: ").strip()
    
    if product_id not in rag.product_stores:
        rag.build_product_store(product_id)
    
    print(f"\n{'='*80}")
    print(f"제품 {product_id} 대화형 모드")
    print(f"명령어: 'detail' - 검색 결과 상세, 'verbose' - 더 자세히")
    print(f"{'='*80}\n")
    
    show_detail = args.show_retrieval
    verbose_mode = args.verbose
    
    while True:
        try:
            user_input = input("\n질문: ").strip()
            
            if user_input.lower() in ['exit', 'quit', '종료']:
                break
            elif user_input.lower() == 'detail':
                show_detail = not show_detail
                print(f"검색 결과 상세 표시: {'ON' if show_detail else 'OFF'}")
                continue
            elif user_input.lower() == 'verbose':
                verbose_mode = not verbose_mode
                print(f"Verbose 모드: {'ON' if verbose_mode else 'OFF'}")
                continue
            
            if user_input:
                result = rag.query(product_id, user_input, show_retrieval=show_detail, verbose=verbose_mode)
                print("\n" + "="*80)
                print(result["answer"])
                print("="*80)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()