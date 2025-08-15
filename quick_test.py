from generate_test_cases import TestCaseGenerator
gen = TestCaseGenerator('AdventureWorksDemoDataProducts_with_embedding.json', 'test_case')
result = gen._determine_category('Camping Tent', 'Waterproof tent for outdoor camping')
print('Camping Tent:', result)
