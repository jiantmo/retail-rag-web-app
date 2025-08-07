#!/usr/bin/env python3
"""
Advanced Product Question Generator for Recommendation Engine
Generates 100 diverse, natural question sets for all products
Total output: 192,000 questions (384 products × 5 questions × 100 runs)
"""

import json
import os
import random
import re
from typing import List, Dict, Any, Set
import time
from datetime import datetime

class AdvancedQuestionGenerator:
    def __init__(self, input_file: str = "AdventureWorksDemoDataProducts_with_embedding.json"):
        self.input_file = input_file
        self.output_dir = "test_case"
        self.products = []
        
        # Diverse question patterns and approaches
        self.question_styles = {
            'direct_need': [
                "I need {description} for {scenario}",
                "Looking for {description} that can {capability}",
                "What {category} would work best for {use_case}?",
                "Can you recommend {description} suitable for {context}?",
                "I'm searching for {description} with {feature}"
            ],
            'scenario_based': [
                "I'm planning {activity} and need {description}",
                "For {situation}, what {category} would you suggest?",
                "My {person} is into {hobby} - what {category} should I get?",
                "We're going {destination} and need {description}",
                "I'll be {activity} - any {category} recommendations?"
            ],
            'feature_focused': [
                "Do you have {category} with {specific_feature}?",
                "What {category} offers {benefit}?",
                "I want {category} that has {characteristic}",
                "Can you show me {category} featuring {attribute}?",
                "Any {category} that comes with {inclusion}?"
            ],
            'budget_conscious': [
                "What's your best {category} around ${price_range}?",
                "I have ${budget} to spend on {category} - what are my options?",
                "Looking for {category} under ${max_price}",
                "What {category} gives the best value around ${price}?",
                "Any {category} in the ${price_low}-${price_high} range?"
            ],
            'comparison_seeking': [
                "How does {product_name} compare to similar {category}?",
                "Is {product_name} worth the price compared to alternatives?",
                "What makes {product_name} different from other {category}?",
                "Should I choose {product_name} or something else?",
                "Why would someone pick {product_name} over cheaper {category}?"
            ],
            'problem_solving': [
                "I keep having issues with {problem} - what {category} could help?",
                "What {category} solves the problem of {pain_point}?",
                "I need {category} that won't {common_issue}",
                "Looking for {category} to overcome {challenge}",
                "What {category} addresses {concern} effectively?"
            ],
            'conversational': [
                "Hey, do you guys carry {description}?",
                "My friend recommended getting {category} - what do you think?",
                "I heard good things about {category} for {use} - any suggestions?",
                "Everyone keeps talking about {category} - what's the deal?",
                "I'm totally new to {activity} - what {category} should I start with?"
            ]
        }
        
        # Rich vocabulary for natural variation
        self.descriptors = {
            'quality': ['high-quality', 'premium', 'durable', 'reliable', 'top-notch', 'excellent', 'superior', 'robust'],
            'size': ['compact', 'spacious', 'large', 'roomy', 'generous', 'ample', 'substantial', 'oversized'],
            'convenience': ['easy-to-use', 'user-friendly', 'convenient', 'hassle-free', 'straightforward', 'simple'],
            'performance': ['high-performance', 'efficient', 'effective', 'powerful', 'capable', 'versatile'],
            'durability': ['long-lasting', 'sturdy', 'tough', 'resilient', 'heavy-duty', 'rugged'],
            'comfort': ['comfortable', 'cozy', 'ergonomic', 'cushioned', 'supportive', 'plush']
        }
        
        # Activity and scenario contexts
        self.contexts = {
            'outdoor_activities': ['camping', 'hiking', 'backpacking', 'climbing', 'fishing', 'hunting'],
            'sports': ['running', 'cycling', 'swimming', 'surfing', 'skiing', 'basketball'],
            'travel': ['vacation', 'business trip', 'weekend getaway', 'international travel', 'road trip'],
            'daily_life': ['work', 'school', 'commuting', 'errands', 'social events', 'casual wear'],
            'weather': ['rainy weather', 'cold conditions', 'hot climate', 'windy days', 'snow'],
            'seasons': ['summer activities', 'winter sports', 'spring outings', 'fall adventures']
        }

    def load_products(self) -> None:
        """Load and validate product data"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.products = data if isinstance(data, list) else [data]
            print(f"✅ Loaded {len(self.products)} products")
        except Exception as e:
            raise Exception(f"Failed to load product data: {e}")

    def extract_product_features(self, product: Dict) -> Dict[str, Any]:
        """Extract and analyze product characteristics for question generation"""
        name = product.get('Name', 'Unknown Product')
        price = float(product.get('Price', 0))
        description = product.get('Description') or ''
        description = description.replace('\n', ' ') if description else ''
        
        # Detect product category
        category = self._detect_category(name, description)
        
        # Extract key features
        features = self._extract_features(description)
        
        # Generate price contexts
        price_ranges = self._generate_price_contexts(price)
        
        # Determine use cases
        use_cases = self._determine_use_cases(category, description)
        
        return {
            'name': name,
            'category': category,
            'price': price,
            'description': description,
            'features': features,
            'price_contexts': price_ranges,
            'use_cases': use_cases,
            'problems_solved': self._identify_problems_solved(description, category)
        }

    def _detect_category(self, name: str, description: str) -> str:
        """Intelligently detect product category"""
        text = f"{name} {description}".lower()
        
        categories = {
            'tent': ['tent'],
            'sleeping bag': ['sleeping bag', 'bag'],
            'surfboard': ['surfboard', 'board'],
            'jacket': ['jacket'],
            'coat': ['coat'],
            'vest': ['vest'],
            'shoes': ['shoe', 'boot', 'sneaker'],
            'shorts': ['short'],
            'pants': ['pant', 'legging'],
            'hoodie': ['hoodie'],
            'sweatshirt': ['sweatshirt'],
            'backpack': ['pack', 'backpack'],
            'equipment': ['snorkel', 'compass', 'gear']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'product'

    def _extract_features(self, description: str) -> List[str]:
        """Extract key product features from description"""
        features = []
        desc_lower = description.lower()
        
        feature_patterns = {
            'waterproof': ['waterproof', 'water resistant', 'weather protection'],
            'lightweight': ['lightweight', 'light weight', 'portable'],
            'durable': ['durable', 'rugged', 'long-lasting', 'sturdy'],
            'easy setup': ['easy', 'quick', 'simple setup', 'color coded'],
            'spacious': ['spacious', 'roomy', 'large', 'super-sized'],
            'breathable': ['breathable', 'ventilation', 'airflow'],
            'insulated': ['insulated', 'warm', 'thermal'],
            'versatile': ['versatile', 'multi', 'various'],
            'comfortable': ['comfortable', 'ergonomic', 'cushioned'],
            'packable': ['packable', 'compact', 'foldable']
        }
        
        for feature, keywords in feature_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                features.append(feature)
        
        return features[:5]  # Limit to top 5 features

    def _generate_price_contexts(self, price: float) -> Dict[str, str]:
        """Generate various price-related contexts"""
        return {
            'budget': f"{int(price * 0.9)}-{int(price * 1.1)}",
            'under': str(int(price * 1.2)),
            'around': str(int(price)),
            'range_low': str(int(price * 0.8)),
            'range_high': str(int(price * 1.2))
        }

    def _determine_use_cases(self, category: str, description: str) -> List[str]:
        """Determine likely use cases for the product"""
        use_case_mapping = {
            'tent': ['family camping', 'backpacking', 'festival camping', 'car camping'],
            'sleeping bag': ['cold weather camping', 'backpacking', 'car camping', 'emergency preparedness'],
            'surfboard': ['surfing', 'beach activities', 'water sports', 'surf lessons'],
            'jacket': ['outdoor activities', 'cold weather', 'layering', 'casual wear'],
            'shoes': ['running', 'hiking', 'casual wear', 'sports activities'],
            'backpack': ['hiking', 'travel', 'daily commute', 'school']
        }
        
        return use_case_mapping.get(category, ['general use', 'outdoor activities'])

    def _identify_problems_solved(self, description: str, category: str) -> List[str]:
        """Identify what problems this product solves"""
        problems = []
        desc_lower = description.lower()
        
        problem_indicators = {
            'weather protection': ['waterproof', 'weather', 'rain', 'wind'],
            'comfort issues': ['comfortable', 'ergonomic', 'cushioned', 'soft'],
            'durability concerns': ['durable', 'long-lasting', 'rugged', 'sturdy'],
            'setup difficulties': ['easy', 'quick', 'simple', 'color coded'],
            'storage problems': ['pockets', 'storage', 'organization', 'vestibule'],
            'weight issues': ['lightweight', 'portable', 'compact']
        }
        
        for problem, indicators in problem_indicators.items():
            if any(indicator in desc_lower for indicator in indicators):
                problems.append(problem)
        
        return problems

    def generate_diverse_questions(self, product_features: Dict, run_id: int) -> List[str]:
        """Generate 5 diverse questions for a product with maximum variation"""
        # Use run_id and product name as seed for reproducible but varied results
        random.seed(hash(f"{run_id}_{product_features['name']}_{time.time()}"))
        
        questions = []
        used_styles = set()
        
        # Ensure we use different question styles
        available_styles = list(self.question_styles.keys())
        random.shuffle(available_styles)
        
        # Generate 4 questions without product name
        for i in range(4):
            style = available_styles[i % len(available_styles)]
            while style in used_styles and len(used_styles) < len(available_styles):
                style = random.choice(available_styles)
            used_styles.add(style)
            
            question = self._generate_question_by_style(style, product_features, False)
            questions.append(question)
        
        # Generate 1 question with product name
        name_style = random.choice([s for s in available_styles if s not in used_styles] or available_styles)
        name_question = self._generate_question_by_style(name_style, product_features, True)
        questions.append(name_question)
        
        # Shuffle to randomize position of name-based question
        random.shuffle(questions)
        
        return questions

    def _generate_question_by_style(self, style: str, features: Dict, include_name: bool) -> str:
        """Generate a question using a specific style"""
        templates = self.question_styles[style]
        template = random.choice(templates)
        
        # Prepare replacement variables
        replacements = self._prepare_replacements(features, include_name)
        
        try:
            # Replace placeholders in template
            question = template.format(**replacements)
            return self._polish_question(question)
        except KeyError:
            # Fallback if template has missing variables
            return self._generate_fallback_question(features, include_name)

    def _prepare_replacements(self, features: Dict, include_name: bool) -> Dict[str, str]:
        """Prepare all possible replacement variables for templates"""
        category = features['category']
        name = features['name']
        price = features['price']
        
        # Add descriptors for variation
        quality_desc = random.choice(self.descriptors['quality'])
        size_desc = random.choice(self.descriptors['size'])
        
        replacements = {
            'category': category,
            'product_name': name if include_name else category,
            'description': f"{quality_desc} {category}",
            'scenario': random.choice(features['use_cases']),
            'capability': random.choice(features['features']) if features['features'] else 'perform well',
            'use_case': random.choice(features['use_cases']),
            'context': random.choice(self.contexts['outdoor_activities']),
            'feature': random.choice(features['features']) if features['features'] else 'quality construction',
            'activity': random.choice(self.contexts['outdoor_activities']),
            'situation': random.choice(self.contexts['travel']),
            'person': random.choice(['friend', 'family member', 'colleague']),
            'hobby': random.choice(self.contexts['sports']),
            'destination': random.choice(['camping', 'the mountains', 'the beach']),
            'specific_feature': random.choice(features['features']) if features['features'] else 'good quality',
            'benefit': random.choice(['durability', 'comfort', 'performance', 'reliability']),
            'characteristic': random.choice(features['features']) if features['features'] else 'quality construction',
            'attribute': random.choice(['excellent build quality', 'innovative design', 'superior materials']),
            'inclusion': random.choice(['warranty', 'accessories', 'free shipping']),
            'price_range': features['price_contexts']['budget'],
            'budget': features['price_contexts']['around'],
            'max_price': features['price_contexts']['under'],
            'price': features['price_contexts']['around'],
            'price_low': features['price_contexts']['range_low'],
            'price_high': features['price_contexts']['range_high'],
            'problem': random.choice(features['problems_solved']) if features['problems_solved'] else 'quality issues',
            'pain_point': random.choice(['poor durability', 'uncomfortable fit', 'difficult setup']),
            'common_issue': random.choice(['break easily', 'wear out quickly', 'disappoint me']),
            'challenge': random.choice(['extreme weather', 'heavy use', 'long trips']),
            'concern': random.choice(['quality', 'durability', 'value for money']),
            'use': random.choice(features['use_cases'])
        }
        
        return replacements

    def _polish_question(self, question: str) -> str:
        """Polish and clean up the generated question"""
        # Capitalize first letter
        question = question.strip()
        if question:
            question = question[0].upper() + question[1:]
        
        # Ensure proper punctuation
        if not question.endswith(('?', '.', '!')):
            if '?' in question or question.lower().startswith(('what', 'how', 'can', 'do', 'is', 'are')):
                question += '?'
            else:
                question += '.'
        
        return question

    def _generate_fallback_question(self, features: Dict, include_name: bool) -> str:
        """Generate a simple fallback question"""
        category = features['category']
        name = features['name']
        
        if include_name:
            return f"What can you tell me about the {name}?"
        else:
            return f"What {category} would you recommend for general use?"

    def generate_run(self, run_id: int) -> List[Dict]:
        """Generate questions for all products in one run"""
        print(f"Generating run {run_id}/100...")
        
        run_data = []
        for i, product in enumerate(self.products):
            if i % 50 == 0:
                print(f"  Processing product {i+1}/{len(self.products)}")
            
            features = self.extract_product_features(product)
            questions = self.generate_diverse_questions(features, run_id)
            
            product_data = {
                "name": features['name'],
                "description": features['description'],
                "questions": questions
            }
            run_data.append(product_data)
        
        return run_data

    def save_run(self, run_data: List[Dict], run_id: int) -> None:
        """Save a run's data to JSON file"""
        filename = f"questions_run_{run_id:03d}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)

    def generate_all_runs(self) -> None:
        """Generate all 100 runs"""
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        start_time = time.time()
        print(f"🚀 Starting generation of 100 question sets for {len(self.products)} products")
        print(f"📊 Total questions to generate: {len(self.products) * 5 * 100:,}")
        print(f"📁 Output directory: {self.output_dir}")
        print("-" * 60)
        
        for run_id in range(1, 101):
            try:
                run_start = time.time()
                run_data = self.generate_run(run_id)
                self.save_run(run_data, run_id)
                
                run_duration = time.time() - run_start
                elapsed = time.time() - start_time
                estimated_total = elapsed * 100 / run_id
                remaining = estimated_total - elapsed
                
                print(f"✅ Run {run_id} completed in {run_duration:.1f}s | "
                      f"Elapsed: {elapsed/60:.1f}m | ETA: {remaining/60:.1f}m")
                
            except Exception as e:
                print(f"❌ Error in run {run_id}: {e}")
                continue
        
        total_duration = time.time() - start_time
        print("-" * 60)
        print(f"🎉 All 100 runs completed!")
        print(f"⏱️ Total time: {total_duration/60:.1f} minutes")
        print(f"📁 Files saved in: {self.output_dir}/")
        print(f"📊 Total questions generated: {len(self.products) * 5 * 100:,}")

def main():
    generator = AdvancedQuestionGenerator()
    
    try:
        generator.load_products()
        generator.generate_all_runs()
        print("\n✨ Question generation completed successfully!")
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
