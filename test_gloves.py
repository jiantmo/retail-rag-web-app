from multi_thread_agentic_search import AgenticSearchClient
import json

client = AgenticSearchClient()
result = client.search('gloves')
print('Result count:', result['result_count'])
print('Success:', result['success'])
response_data = result['response_data']
print('API Success:', response_data.get('Success'))
print('Error:', response_data.get('Error', 'None'))
if result['result_count'] > 0:
    print('Products found:')
    for p in result['extracted_products'][:5]:
        print(f'  - {p["name"]} - ${p["price"]}')
else:
    print('No products found')
    print('Response summary:', response_data.get('Result', {}).get('Summary', 'No summary'))
