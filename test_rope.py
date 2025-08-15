from generate_test_cases import TestCaseGenerator
gen = TestCaseGenerator('AdventureWorksDemoDataProducts_with_embedding.json', 'test_case')
result = gen._determine_category('Skiplyco Jumping Rope', 'Lightweight, durable and comfortable handle makes it easy to grasp and carry. Dual ball bearing system and slight cable can pass through the air quickly, thus increasing the speed. The rope can be adjusted the length you want according to your height.')
print('Jumping Rope:', result)
