#!/usr/bin/env python3
"""
Test Case Generator for Retail RAG Web App

This script generates test case files using AdventureWorksDemoDataProducts_with_embedding.json
as the source data. Each test case file contains products with 5 specific types of questions:
1. Exact word match question (includes product name)
2. Price range question (based on product price)
3. Description question (generated from product description)
4. Attribute value question (based on product attributes)
5. Category question (based on product category/description)
"""

import json
import os
import random
import re
from typing import List, Dict, Any

class TestCaseGenerator:
    def __init__(self, source_file: str, output_dir: str):
        self.source_file = source_file
        self.output_dir = output_dir
        self.products = []
        self.categories = self._define_categories()
        
    def _define_categories(self) -> Dict[str, List[str]]:
        """Define product categories and related keywords for question generation"""
        return {
            "tent": {
                "primary": ["tent", "shelter", "camping"],
                "secondary": ["setup", "poles", "stakes", "rainfly", "waterproof", "outdoor"],
                "weight": 10
            },
            "sleeping": {
                "primary": ["sleeping bag", "sleep", "bag", "down", "fill"],
                "secondary": ["temperature", "rating", "insulation", "mummy"],
                "weight": 8
            },
            "clothing": {
                "primary": ["shirt", "jacket", "coat", "vest", "sweatshirt", "hoodie", "apparel"],
                "secondary": ["wear", "fabric", "sleeve", "closure", "zipper"],
                "weight": 9
            },
            "footwear": {
                "primary": ["shoes", "boots", "sneakers", "sandals", "sole"],
                "secondary": ["walking", "running", "size", "foot"],
                "weight": 10
            },
            "shorts_pants": {
                "primary": ["shorts", "pants", "leggings", "trousers"],
                "secondary": ["waist", "leg", "inseam", "fit"],
                "weight": 10
            },
            "backpack": {
                "primary": ["backpack", "pack", "bag"],
                "secondary": ["carry", "storage", "volume", "liter", "strap"],
                "weight": 9
            },
            "bike": {
                "primary": ["bike", "bicycle", "cycling", "mountain bike"],
                "secondary": ["riding", "wheel", "frame", "pedal"],
                "weight": 10
            },
            "helmet": {
                "primary": ["helmet", "head protection"],
                "secondary": ["safety", "impact", "certified"],
                "weight": 10
            },
            "gloves": {
                "primary": ["gloves", "mittens", "hand"],
                "secondary": ["grip", "finger", "palm"],
                "weight": 10
            },
            "hat": {
                "primary": ["hat", "cap", "beanie", "headwear"],
                "secondary": ["head", "brim", "visor"],
                "weight": 10
            },
            "accessory": {
                "primary": ["accessory", "gear", "equipment", "tool", "ski", "skis", "snowboard", "surfboard", "paddle", "kayak", "windsurf", "lantern", "watch", "chair", "stool", "poles", "rope"],
                "secondary": ["utility", "feature", "outdoor", "sport", "recreation"],
                "weight": 3
            }
        }
    
    def load_products(self):
        """Load products from the source JSON file"""
        with open(self.source_file, 'r', encoding='utf-8') as f:
            self.products = json.load(f)
        print(f"Loaded {len(self.products)} products from {self.source_file}")
    
    def _extract_attributes(self, attribute_values_str: str) -> List[Dict[str, Any]]:
        """Extract attribute names and values from the AttributeValues string"""
        try:
            if not attribute_values_str or attribute_values_str == "[]":
                return []
            
            # Parse the string as JSON-like data
            attributes = eval(attribute_values_str)
            attr_list = []
            
            for attr in attributes:
                if 'Name' in attr and 'TextValue' in attr:
                    attr_name = attr['Name']
                    values = attr['TextValue'].split('|')
                    for value in values:
                        if value.strip():
                            attr_list.append({
                                "name": attr_name,
                                "value": value.strip()
                            })
                    
            return attr_list
        except:
            return []
    
    def _determine_category(self, name: str, description: str) -> str:
        """Determine product category based on name and description using weighted scoring"""
        # Handle None values
        if name is None:
            name = ""
        if description is None:
            description = ""
            
        text = (name + " " + description).lower()
        name_lower = name.lower()
        
        # Calculate scores for each category
        category_scores = {}
        
        for category, keywords in self.categories.items():
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
                    else:
                        score += 5 * weight
            
            # Check secondary keywords (lower score)
            for keyword in secondary_keywords:
                if keyword.lower() in text:
                    score += 1 * weight
            
            # Exact name matches get bonus points
            if any(keyword.lower() == name_lower for keyword in primary_keywords):
                score += 20 * weight
            
            category_scores[category] = score
        
        # Special bonus for ski equipment combinations
        if "ski" in text and "poles" in text and "accessory" in category_scores:
            category_scores["accessory"] += 50  # Strong bonus for ski poles
        
        # Apply penalties for obvious mismatches
        category_scores = self._apply_category_penalties(name_lower, text, category_scores)
        
        # Return category with highest score
        best_category = max(category_scores, key=category_scores.get)
        
        # If no significant match found, try specific product type detection
        if category_scores[best_category] <= 0:
            return self._detect_specific_product_type(name, description)
        
        return best_category
    
    def _apply_category_penalties(self, name_lower: str, text: str, scores: Dict[str, int]) -> Dict[str, int]:
        """Apply penalties for obvious category mismatches"""
        
        # Penalties for obvious mismatches
        penalties = {
            # If it's clearly clothing, penalize non-clothing categories
            "clothing_indicators": {
                "keywords": ["jacket", "coat", "shirt", "vest", "sweatshirt", "hoodie"],
                "penalty_categories": ["tent", "bike", "footwear", "shorts_pants", "backpack"],
                "penalty": -50
            },
            # If it's clearly footwear, penalize other categories
            "footwear_indicators": {
                "keywords": ["shoes", "boots", "sneakers", "sandals"],
                "penalty_categories": ["tent", "clothing", "bike", "shorts_pants", "backpack"],
                "penalty": -50
            },
            # If it's clearly shorts/pants, penalize other categories
            "bottoms_indicators": {
                "keywords": ["shorts", "pants", "leggings", "trousers"],
                "penalty_categories": ["tent", "clothing", "bike", "footwear", "backpack"],
                "penalty": -50
            },
            # If it's clearly bike-related, penalize other categories
            "bike_indicators": {
                "keywords": ["bike", "bicycle", "cycling"],
                "penalty_categories": ["tent", "clothing", "footwear", "shorts_pants"],
                "penalty": -30
            },
            # If it's jumping rope, penalize glove category even if it has grip/grasp
            "rope_indicators": {
                "keywords": ["jumping rope", "rope"],
                "penalty_categories": ["gloves"],
                "penalty": -60
            }
        }
        
        for rule_name, rule in penalties.items():
            if any(keyword in name_lower for keyword in rule["keywords"]):
                for category in rule["penalty_categories"]:
                    if category in scores:
                        scores[category] += rule["penalty"]
        
        return scores
    
    def _detect_specific_product_type(self, name: str, description: str) -> str:
        """Detect specific product types for edge cases"""
        text = (name + " " + description).lower()
        name_lower = name.lower()
        
        # Specific product type mappings - check name first for more accurate matching
        name_patterns = {
            "shorts": "shorts_pants",
            "pants": "shorts_pants", 
            "leggings": "shorts_pants",
            "wetsuit": "clothing",
            "goggles": "accessory",
            "binocular": "accessory",
            "paddle": "accessory",
            "surfboard": "accessory",
            "snowboard": "accessory",
            "skateboard": "accessory",
            "ski": "accessory",  # Add ski equipment
            "skis": "accessory", # Add plural form
            "lantern": "accessory",
            "stovetop": "accessory",
            "mug": "accessory",
            "mask": "accessory",
            "snorkel": "accessory",
            "pump": "accessory",
            "kayak": "accessory",  # Add kayak
            "canoe": "accessory",  # Add canoe
            "windsurf": "accessory",  # Add windsurf
            "surfing": "accessory",  # Add surfing variants
            "board": "accessory",  # Generic board products
            "scarf": "clothing",  # Add scarf to clothing
            "gloves": "clothing",  # Add gloves
            "mittens": "clothing",  # Add mittens
            "watch": "accessory",  # Add watch
            "chair": "accessory",  # Add camping chair
            "stool": "accessory",  # Add stool
            "table": "accessory"   # Add table
        }
        
        # Check name first for exact matches
        for keyword, category in name_patterns.items():
            if keyword in name_lower:
                return category
        
        # Description patterns for when name doesn't have clear indicators
        description_patterns = {
            "cooking": "accessory",
            "coffee": "accessory",
            "yoga mat": "accessory",
            "exercise mat": "accessory",
            "tire pump": "accessory"
        }
        
        for keyword, category in description_patterns.items():
            if keyword in text:
                return category
        
        return "accessory"  # default fallback
    
    def _generate_exact_word_question(self, name: str, category: str) -> str:
        """Generate question that includes the exact product name"""
        templates = [
            f"I heard good things about {category} for {name} - any suggestions?",
            f"Can you tell me more about the {name}?",
            f"What's your opinion on {name}?",
            f"I'm considering buying {name} - is it worth it?",
            f"How does {name} compare to other {category} options?"
        ]
        return random.choice(templates)
    
    def _generate_price_question(self, price: float, category: str) -> str:
        """Generate price-related question based on product price"""
        # Create price ranges around the actual price
        lower_bound = max(10, int(price * 0.8))
        upper_bound = int(price * 1.2)
        
        templates = [
            f"I have ${int(price)} to spend on {category} - what are my options?",
            f"What {category} can I get for around ${int(price)}?",
            f"Looking for {category} in the ${lower_bound}-${upper_bound} range - any recommendations?",
            f"What's the best {category} I can get for under ${upper_bound}?",
            f"I'm budgeting ${int(price)} for {category} - what do you suggest?"
        ]
        return random.choice(templates)
    
    def _generate_description_question(self, description: str, category: str) -> str:
        """Generate question based on product description"""
        # Handle None description
        if description is None:
            description = ""
            
        # Extract key features from description
        key_phrases = []
        desc_lower = description.lower()
        
        # Common feature keywords to look for
        feature_keywords = [
            "waterproof", "lightweight", "durable", "comfortable", "breathable",
            "insulated", "compact", "adjustable", "protection", "support",
            "ventilation", "weather", "warmth", "comfort", "quality",
            "performance", "reliable", "sturdy", "flexible", "versatile"
        ]
        
        for keyword in feature_keywords:
            if keyword in desc_lower:
                key_phrases.append(keyword)
        
        if key_phrases:
            feature = random.choice(key_phrases)
            templates = [
                f"I need {category} that is {feature}.",
                f"What {category} offers {feature}?",
                f"Looking for {category} with {feature} - any suggestions?",
                f"Can you recommend {category} that provides {feature}?"
            ]
        else:
            templates = [
                f"I need {category} that won't disappoint me.",
                f"What {category} offers good performance?",
                f"Looking for reliable {category} - any suggestions?",
                f"Can you recommend quality {category}?"
            ]
        
        return random.choice(templates)
    
    def _generate_attribute_question(self, attributes: List[Dict[str, Any]], category: str) -> str:
        """Generate question based on product attributes"""
        if attributes:
            # Use a random attribute for the question
            attribute = random.choice(attributes)
            attr_name = attribute['name'].lower()
            attr_value = attribute['value'].lower()
            
            templates = [
                f"What {category} would work best for outdoor activities?",
                f"I need {category} with good features - what do you recommend?",
                f"What {category} comes in {attr_value} {attr_name}?",
                f"Looking for {category} with premium features.",
                f"What {category} would work best for backpacking?"
            ]
        else:
            templates = [
                f"What {category} would work best for outdoor activities?",
                f"I need {category} with good features - what do you recommend?",
                f"Looking for {category} with premium features.",
                f"What {category} would work best for backpacking?",
                f"Can you suggest {category} for hiking?"
            ]
        
        return random.choice(templates)
    
    def _generate_category_price_question(self, price: float, category: str) -> str:
        """Generate category + price range question"""
        # Create price ranges around the actual price
        lower_bound = max(10, int(price * 0.8))
        upper_bound = int(price * 1.2)
        
        templates = [
            f"Looking for {category} in the ${lower_bound}-${upper_bound} range - any recommendations?",
            f"What {category} can I get for around ${int(price)}?",
            f"I need good {category} within ${lower_bound}-${upper_bound} price range.",
            f"What's the best {category} I can find under ${upper_bound}?",
            f"Budget ${int(price)} for {category} - what are my options?"
        ]
        return random.choice(templates)
    
    def _generate_category_attribute_question(self, attributes: List[Dict[str, Any]], category: str) -> str:
        """Generate category + attribute value question"""
        if attributes:
            # Use a random attribute for the question
            attribute = random.choice(attributes)
            attr_name = attribute['name'].lower()
            attr_value = attribute['value'].lower()
            
            # Special handling for size, color, and common attributes
            if 'size' in attr_name or 'length' in attr_name:
                templates = [
                    f"What {category} comes in {attr_value} size?",
                    f"Do you have {category} available in size {attr_value}?",
                    f"Looking for {category} in {attr_value} - what options do I have?"
                ]
            elif 'color' in attr_name:
                templates = [
                    f"What {category} comes in {attr_value} color?",
                    f"Do you have {attr_value} {category}?",
                    f"Looking for {attr_value} colored {category}."
                ]
            elif 'material' in attr_name or 'fabric' in attr_name:
                templates = [
                    f"What {category} is made of {attr_value}?",
                    f"Do you have {attr_value} {category}?",
                    f"Looking for {category} with {attr_value} material."
                ]
            else:
                templates = [
                    f"What {category} comes in {attr_value} {attr_name}?",
                    f"Do you have {category} with {attr_value} {attr_name}?",
                    f"Looking for {category} featuring {attr_value}."
                ]
        else:
            templates = [
                f"What {category} has the best features?",
                f"Looking for high-quality {category} with good specifications.",
                f"What {category} offers premium features?"
            ]
        
        return random.choice(templates)
        """Generate category-based question"""
        # Handle None description
        if description is None:
            description = ""
            
        desc_lower = description.lower()
        
        # Look for specific features in description
        if "insulated" in desc_lower or "insulation" in desc_lower:
            return f"Do you have {category} with insulated features?"
        elif "waterproof" in desc_lower or "water" in desc_lower:
            return f"Do you have {category} that is waterproof?"
        elif "lightweight" in desc_lower or "light" in desc_lower:
            return f"Do you have lightweight {category}?"
        elif "durable" in desc_lower or "strong" in desc_lower:
            return f"Do you have durable {category}?"
        else:
            templates = [
                f"Do you have {category} for outdoor use?",
                f"What {category} do you recommend for beginners?",
                f"Do you have premium {category}?",
                f"What's your best {category} for hiking?",
                f"Do you have {category} with good reviews?"
            ]
            return random.choice(templates)
    
    def generate_questions_for_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all 5 types of questions for a single product"""
        name = product.get('Name', 'Unknown Product')
        description = product.get('Description', 'Quality product for your needs')
        price = product.get('Price', 100.0)
        attributes = self._extract_attributes(product.get('AttributeValues', '[]'))
        category = self._determine_category(name, description)
        
    def _generate_category_question(self, category: str, description: str) -> str:
        """Generate category-based question"""
        # Handle None description
        if description is None:
            description = ""
            
        desc_lower = description.lower()
        
        # Look for specific features in description
        if "insulated" in desc_lower or "insulation" in desc_lower:
            return f"Do you have {category} with insulated features?"
        elif "waterproof" in desc_lower or "water" in desc_lower:
            return f"Do you have {category} that is waterproof?"
        elif "lightweight" in desc_lower or "light" in desc_lower:
            return f"Do you have lightweight {category}?"
        elif "durable" in desc_lower or "strong" in desc_lower:
            return f"Do you have durable {category}?"
        else:
            templates = [
                f"Do you have {category} for outdoor use?",
                f"What {category} do you recommend for beginners?",
                f"Do you have premium {category}?",
                f"What's your best {category} for hiking?",
                f"Do you have {category} with good reviews?"
            ]
            return random.choice(templates)

    def generate_questions_for_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all 5 types of questions for a single product"""
        name = product.get('Name', 'Unknown Product')
        description = product.get('Description', 'Quality product for your needs')
        price = product.get('Price', 100.0)
        attributes = self._extract_attributes(product.get('AttributeValues', '[]'))
        category = self._determine_category(name, description)
        
        questions = {
            "Exact word": self._generate_exact_word_question(name, category),
            "Category": self._generate_category_question(category, description),
            "Category + Price range": self._generate_category_price_question(price, category),
            "Category + Attribute value": self._generate_category_attribute_question(attributes, category),
            "Description": self._generate_description_question(description, category)
        }
        
        return {
            "name": name,
            "description": description,
            "price": price,
            "attributes": attributes,
            "category": category,
            "questions": questions
        }
    
    def generate_test_case_file(self, file_number: int, products_per_file: int = 192):
        """Generate a single test case file with specified number of products"""
        # Select random products for this file
        selected_products = random.sample(self.products, min(products_per_file, len(self.products)))
        
        test_cases = []
        for product in selected_products:
            test_case = self.generate_questions_for_product(product)
            test_cases.append(test_case)
        
        # Create output filename
        output_file = os.path.join(self.output_dir, f"questions_run_{file_number:03d}.json")
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, indent=2, ensure_ascii=False)
        
        print(f"Generated {output_file} with {len(test_cases)} products")
        return output_file
    
    def generate_all_test_files(self, num_files: int = 10, products_per_file: int = 192):
        """Generate all test case files"""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Generating {num_files} test case files with {products_per_file} products each...")
        
        generated_files = []
        for i in range(1, num_files + 1):
            try:
                file_path = self.generate_test_case_file(i, products_per_file)
                generated_files.append(file_path)
            except Exception as e:
                print(f"Error generating file {i}: {e}")
        
        print(f"\nSuccessfully generated {len(generated_files)} test case files:")
        for file_path in generated_files:
            print(f"  - {file_path}")
        
        return generated_files


def main():
    """Main function to run the test case generator"""
    source_file = "AdventureWorksDemoDataProducts_with_embedding.json"
    output_dir = "test_case"
    
    # Initialize generator
    generator = TestCaseGenerator(source_file, output_dir)
    
    # Load products
    generator.load_products()
    
    # Generate 10 test case files
    generator.generate_all_test_files(num_files=10, products_per_file=192)
    
    print("\nTest case generation completed!")


if __name__ == "__main__":
    main()
