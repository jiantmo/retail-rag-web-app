from multi_thread_agentic_search import AgenticSearchClient
import json

client = AgenticSearchClient()
result = client.search('Do you have premium accessory?')
print('Result count:', result['result_count'])
print('Success:', result['success'])
response_data = result['response_data']
print('API Success:', response_data.get('Success'))
print('Error:', response_data.get('Error', 'None'))
if result['result_count'] > 0:
    print('Products found:')
    for p in result['extracted_products'][:3]:
        print(f'  - {p["name"]} - ${p["price"]}')
