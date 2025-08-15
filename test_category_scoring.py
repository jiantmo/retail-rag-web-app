import json
from generate_test_cases import TestCaseGenerator

# Initialize the generator
generator = TestCaseGenerator("AdventureWorksDemoDataProducts_with_embedding.json", "test_case")

# Test the category determination for "Sifulayaka Skis"
product_name = "Sifulayaka Skis"
product_description = ""  # Assuming empty description

# Print category keywords for debugging
print("Category keywords:")
for category, keywords in generator.categories.items():
    print(f"  {category}: {keywords}")

print("\nTesting category determination for 'Sifulayaka Skis':")

# Get the category
result_category = generator._determine_category(product_name, product_description)
print(f"Final category: {result_category}")

# Let's also manually test the scoring logic
text = (product_name + " " + product_description).lower()
name_lower = product_name.lower()

print(f"\nText being analyzed: '{text}'")
print(f"Name (lowercase): '{name_lower}'")

category_scores = {}

for category, keywords in generator.categories.items():
    score = 0
    primary_keywords = keywords["primary"]
    secondary_keywords = keywords["secondary"]
    weight = keywords["weight"]
    
    # Check primary keywords (higher score)
    for keyword in primary_keywords:
        if keyword.lower() in text:
            # Extra points if keyword is in the name
            if keyword.lower() in name_lower:
                score += 10 * weight
                print(f"  {category}: Found '{keyword}' in name, +{10 * weight} = {score}")
            else:
                score += 5 * weight
                print(f"  {category}: Found '{keyword}' in text, +{5 * weight} = {score}")
    
    # Check secondary keywords (lower score)
    for keyword in secondary_keywords:
        if keyword.lower() in text:
            score += 1 * weight
            print(f"  {category}: Found '{keyword}' (secondary) in text, +{1 * weight} = {score}")
    
    # Exact name matches get bonus points
    if any(keyword.lower() == name_lower for keyword in primary_keywords):
        score += 20 * weight
        print(f"  {category}: Exact name match, +{20 * weight} = {score}")
    
    category_scores[category] = score

print("\nScores before penalties:")
for category, score in category_scores.items():
    print(f"  {category}: {score}")

# Apply penalties
category_scores = generator._apply_category_penalties(name_lower, text, category_scores)

print("\nScores after penalties:")
for category, score in category_scores.items():
    print(f"  {category}: {score}")

# Return category with highest score
best_category = max(category_scores, key=category_scores.get)
print(f"\nBest category: {best_category}")
