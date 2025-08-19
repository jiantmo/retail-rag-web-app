#!/usr/bin/env python3
"""
Unified Relevance Scoring Logic for Search Engine Evaluation
Consistent scoring approach for both Dataverse and Agentic search evaluation
"""

import re
import json
from typing import Dict, List, Set, Tuple, Any, Union
from collections import defaultdict

class UnifiedRelevanceScorer:
    """
    Unified relevance scorer that implements consistent logic for both search systems:
    
    Scoring Scale (0-3):
    - 3: Highly relevant (exact match or very close)
    - 2: Relevant (good match with some criteria met)
    - 1: Somewhat relevant (partial match)
    - 0: Not relevant (no meaningful match)
    
    Question Types:
    1. Exact word – Result is relevant if it contains the exact word/product name
    2. Category – Result is relevant if it belongs to the same category
    3. Category + Attribute – Result is relevant if same category AND attribute value matches
    4. Category + Price – Result is relevant if same category AND price falls within range
    5. Description – Result is relevant if semantically related to the question
    """
    
    def __init__(self):
        # Define category mappings and synonyms
        self.category_mappings = {
            'clothing': ['clothing', 'apparel', 'wear', 'garment', 'shirt', 'jacket', 'coat', 'sweater', 'hoodie', 'vest'],
            'footwear': ['footwear', 'shoes', 'boots', 'sneakers', 'sandals', 'shoe', 'boot'],
            'bike': ['bike', 'bicycle', 'cycling', 'cycle'],
            'accessory': ['accessory', 'accessories', 'gear', 'equipment'],
            'backpack': ['backpack', 'pack', 'bag', 'rucksack'],
            'helmet': ['helmet', 'head protection'],
            'tent': ['tent', 'shelter', 'camping'],
            'gloves': ['gloves', 'glove', 'hand protection'],
            'shorts_pants': ['shorts', 'pants', 'trousers', 'short', 'pant'],
            'hat': ['hat', 'cap', 'beanie'],
            'sleeping': ['sleeping', 'sleep', 'bag']
        }
        
        # Common attribute keywords for matching
        self.attribute_keywords = {
            'color': ['color', 'colour', 'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey'],
            'size': ['size', 'small', 'medium', 'large', 'xl', 'xxl', 's', 'm', 'l'],
            'material': ['material', 'cotton', 'polyester', 'wool', 'leather', 'synthetic', 'fabric', 'nylon'],
            'style': ['style', 'casual', 'formal', 'sport', 'athletic', 'outdoor'],
            'features': ['waterproof', 'breathable', 'insulated', 'lightweight', 'durable']
        }

        # Stop words for text processing
        self.stop_words = {
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her',
            'it', 'its', 'they', 'them', 'their', 'what', 'which', 'who', 'whom', 'this',
            'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the',
            'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by',
            'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'up', 'down', 'in', 'out', 'on', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now', 'good',
            'things', 'compare', 'options', 'suggestions', 'opinion', 'considering',
            'buying', 'worth', 'tell', 'heard', 'show', 'find', 'looking', 'need'
        }
    
    def score_result_relevance(self, result: Union[Dict, str], question_data: Dict, 
                             result_format: str = 'dataverse') -> int:
        """
        Score a single search result based on unified relevance criteria
        
        Args:
            result: Search result (Dict for dataverse, str for agentic parsed product)
            question_data: Original question data with context
            result_format: 'dataverse' or 'agentic' to handle different formats
            
        Returns:
            Relevance score: 0-3 (0=not relevant, 3=highly relevant)
        """
        try:
            question_type = question_data.get('question_type', '').strip()
            question_text = question_data.get('question', '').lower()
            expected_product_name = question_data.get('original_product_name', '').lower()
            expected_category = question_data.get('original_product_category', '').lower()
            expected_price = question_data.get('original_product_price', 0.0)
            expected_attributes = question_data.get('original_product_attributes', [])
            
            # Extract result information based on format
            if result_format == 'agentic':
                result_name, result_price, result_text = self._parse_agentic_result(result)
            else:
                result_name, result_price, result_text = self._parse_dataverse_result(result)
            
            result_category = self._extract_category_from_text(result_text)
            
            # Route to specific scoring method based on question type
            if question_type == "Exact word":
                return self._score_exact_word(question_text, expected_product_name, result_name, result_text)
            
            elif question_type == "Category":
                return self._score_category(expected_category, result_category, result_text)
            
            elif question_type in ["Category + Attribute value", "Attribute value"]:
                return self._score_category_attribute(expected_category, expected_attributes, 
                                                    result_category, result_text, question_text)
            
            elif question_type in ["Category + Price range", "Price range"]:
                return self._score_category_price(expected_category, expected_price, 
                                                result_category, result_price, question_text, result_text)
            
            elif question_type == "Description":
                return self._score_description(question_text, expected_product_name, expected_category,
                                             result_name, result_text)
            
            else:
                # Fallback for unknown question types
                return self._score_general_relevance(expected_product_name, expected_category,
                                                   result_name, result_category, result_text)
        
        except Exception as e:
            print(f"⚠️ Error scoring relevance: {e}")
            return 0
    
    def _parse_agentic_result(self, result: Union[Dict, str]) -> Tuple[str, float, str]:
        """Parse agentic search result format"""
        if isinstance(result, str):
            # Parse from text format
            name_match = re.search(r'Name[:\s]*([^,\n]+)', result, re.IGNORECASE)
            price_match = re.search(r'Price[:\s]*\$?([\d.]+)', result, re.IGNORECASE)
            
            result_name = name_match.group(1).strip() if name_match else ""
            result_price = float(price_match.group(1)) if price_match else 0.0
            result_text = result.lower()
            
        elif isinstance(result, dict):
            # Parse from dict format
            result_name = result.get('Name', result.get('DisplayName', '')).lower()
            result_price = self._extract_price_from_result(result)
            result_text = f"{result_name} {result.get('Description', '')}".lower()
        else:
            result_name = ""
            result_price = 0.0
            result_text = str(result).lower()
        
        return result_name, result_price, result_text
    
    def _parse_dataverse_result(self, result: Dict) -> Tuple[str, float, str]:
        """Parse dataverse search result format"""
        result_name = result.get('DisplayName', result.get('cr4a3_productname', '')).lower()
        result_price = self._extract_price_from_result(result)
        result_description = result.get('Description', '').lower()
        result_text = f"{result_name} {result_description}".lower()
        
        return result_name, result_price, result_text
    
    def _extract_price_from_result(self, result: Dict) -> float:
        """Extract price from result with multiple fallback approaches"""
        price_fields = ['Price', 'cr4a3_price', 'ListPrice', 'BasePrice']
        
        for field in price_fields:
            if field in result and result[field] is not None:
                try:
                    return float(result[field])
                except (ValueError, TypeError):
                    continue
        
        return 0.0
    
    def _extract_category_from_text(self, text: str) -> str:
        """Extract category from text using keyword matching"""
        text_lower = text.lower()
        
        for category, keywords in self.category_mappings.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return "unknown"
    
    def _score_exact_word(self, question_text: str, expected_product_name: str, 
                         result_name: str, result_text: str) -> int:
        """
        Score for "Exact word" questions following SCORING_LOGIC_SUMMARY.md
        
        Scoring Logic:
        - 3 points: Product name coverage ≥ 70%
        - 2 points: Partial product name (≥30%) + meaningful query words (≥30%)
        - 1 point: Meaningful query words only (≥30% coverage)
        - 0 points: No significant matches
        """
        try:
            # Extract product names from question using documented patterns
            product_names_in_question = self._extract_product_names_from_question(question_text)
            meaningful_query_words = self._extract_meaningful_words(question_text)
            result_words = self._extract_meaningful_words(result_text)
            
            if not meaningful_query_words:
                return 0
            
            # Check for product name coverage
            max_product_coverage = 0.0
            for product_name in product_names_in_question:
                if product_name and len(product_name.strip()) > 2:
                    product_words = set(product_name.lower().split())
                    if product_words:
                        result_product_words = set(word for word in result_words if word in product_words)
                        coverage = len(result_product_words) / len(product_words)
                        max_product_coverage = max(max_product_coverage, coverage)
            
            # Check meaningful query word coverage
            query_word_overlap = len(meaningful_query_words & result_words)
            query_word_coverage = query_word_overlap / len(meaningful_query_words) if meaningful_query_words else 0
            
            # Apply documented scoring logic
            if max_product_coverage >= 0.7:
                return 3  # Product name coverage ≥ 70%
            elif max_product_coverage >= 0.3 and query_word_coverage >= 0.3:
                return 2  # Partial product name (≥30%) + meaningful query words (≥30%)
            elif query_word_coverage >= 0.3:
                return 1  # Meaningful query words only (≥30% coverage)
            else:
                return 0  # No significant matches
                
        except Exception as e:
            print(f"Warning: Error in exact word scoring: {e}")
            return 0
    
    def _score_category(self, expected_category: str, result_category: str, result_text: str) -> int:
        """
        Score for "Category" questions following SCORING_LOGIC_SUMMARY.md
        
        Scoring Logic:
        - 3 points: Direct category match
        - 2 points: Strong category match via synonyms/mappings  
        - 1 point: Weak category match
        - 0 points: No category relevance
        """
        try:
            # Direct category match
            if expected_category == result_category and expected_category != "unknown":
                return 3
            
            # Get category keywords for expected category
            expected_keywords = self.category_mappings.get(expected_category, [expected_category])
            
            # Count keyword matches in result text
            keyword_matches = 0
            strong_matches = 0
            
            for keyword in expected_keywords:
                if keyword in result_text:
                    keyword_matches += 1
                    # Consider main category words as strong matches
                    if keyword in [expected_category] or len(keyword) > 4:
                        strong_matches += 1
            
            # Apply documented scoring logic
            if strong_matches >= 1 and keyword_matches >= 2:
                return 2  # Strong category match via synonyms/mappings
            elif keyword_matches >= 1:
                return 1  # Weak category match  
            else:
                return 0  # No category relevance
                
        except Exception as e:
            print(f"Warning: Error in category scoring: {e}")
            return 0
    
    def _score_category_attribute(self, expected_category: str, expected_attributes: List[Dict],
                                result_category: str, result_text: str, question_text: str) -> int:
        """
        Score for "Category + Attribute" questions following SCORING_LOGIC_SUMMARY.md
        
        Scoring Logic:
        - 3 points: Perfect match (correct category + all attributes)
        - 2 points: Good match (correct category + some attributes)
        - 1 point: Partial match (attributes found but weak category) 
        - 0 points: Poor category match or no attributes
        """
        try:
            # Check category match
            category_match = False
            if expected_category == result_category and expected_category != "unknown":
                category_match = True
            else:
                # Check for category keywords
                expected_keywords = self.category_mappings.get(expected_category, [expected_category])
                for keyword in expected_keywords:
                    if keyword in result_text:
                        category_match = True
                        break
            
            # Check attribute matches
            attribute_score = 0
            total_expected_attributes = len(expected_attributes)
            matched_attributes = 0
            
            # Check expected attributes
            for attr in expected_attributes:
                attr_name = attr.get('name', attr.get('Name', '')).lower()
                attr_value = attr.get('value', attr.get('Value', '')).lower()
                
                if attr_value and (attr_value in result_text or attr_value in question_text.lower()):
                    matched_attributes += 1
                elif attr_name and attr_name in result_text:
                    matched_attributes += 0.5  # Partial credit for attribute name match
            
            # Check for attribute keywords in question
            question_lower = question_text.lower()
            for attr_type, keywords in self.attribute_keywords.items():
                for keyword in keywords:
                    if keyword in question_lower and keyword in result_text:
                        matched_attributes += 0.5
            
            # Calculate attribute match ratio
            if total_expected_attributes > 0:
                attr_match_ratio = matched_attributes / total_expected_attributes
            else:
                attr_match_ratio = 1.0 if matched_attributes > 0 else 0.0
            
            # Apply documented scoring logic
            if category_match and attr_match_ratio >= 0.8:
                return 3  # Perfect match (correct category + all attributes)
            elif category_match and attr_match_ratio >= 0.3:
                return 2  # Good match (correct category + some attributes)
            elif attr_match_ratio >= 0.3:
                return 1  # Partial match (attributes found but weak category)
            else:
                return 0  # Poor category match or no attributes
                
        except Exception as e:
            print(f"Warning: Error in category+attribute scoring: {e}")
            return 0
    
    def _score_category_price(self, expected_category: str, expected_price: float,
                            result_category: str, result_price: float, 
                            question_text: str, result_text: str) -> int:
        """
        Score for "Category + Price" questions following SCORING_LOGIC_SUMMARY.md
        
        Scoring Logic:
        - 3 points: Perfect match (correct category + price in range)
        - 2 points: Price match but weak category OR strong category but price outside range
        - 1 point: Category match but price outside range
        - 0 points: Neither category nor price match well
        """
        try:
            # Check category match
            category_match = False
            if expected_category == result_category and expected_category != "unknown":
                category_match = True
            else:
                # Check for category keywords
                expected_keywords = self.category_mappings.get(expected_category, [expected_category])
                for keyword in expected_keywords:
                    if keyword in result_text:
                        category_match = True
                        break
            
            # Extract price range from question or use expected price
            price_ranges = self._extract_price_ranges_from_question(question_text)
            
            price_match = False
            price_in_range = False
            
            if price_ranges:
                # Use extracted ranges from question
                for min_price, max_price in price_ranges:
                    if min_price <= result_price <= max_price:
                        price_in_range = True
                        break
                    if abs(result_price - min_price) / max(min_price, 1) <= 0.3 or abs(result_price - max_price) / max(max_price, 1) <= 0.3:
                        price_match = True
            else:
                # Use expected price with tolerance
                if expected_price > 0:
                    price_tolerance = expected_price * 0.2  # ±20% tolerance for good match
                    price_loose_tolerance = expected_price * 0.5  # ±50% tolerance for weak match
                    
                    if abs(result_price - expected_price) <= price_tolerance:
                        price_in_range = True
                    elif abs(result_price - expected_price) <= price_loose_tolerance:
                        price_match = True
            
            # Apply documented scoring logic
            if category_match and price_in_range:
                return 3  # Perfect match (correct category + price in range)
            elif price_in_range or (category_match and price_match):
                return 2  # Price match but weak category OR strong category but price outside range
            elif category_match:
                return 1  # Category match but price outside range
            else:
                return 0  # Neither category nor price match well
                
        except Exception as e:
            print(f"Warning: Error in category+price scoring: {e}")
            return 0
    
    def _score_description(self, question_text: str, expected_product_name: str, 
                         expected_category: str, result_name: str, result_text: str) -> int:
        """
        Score for "Description" questions following SCORING_LOGIC_SUMMARY.md
        
        Scoring Logic (Complex adaptive weighting based on available data):
        - When rich description data is available: Summary(50%) + Description(30%) + Name(15%) + Category(5%)
        - When only basic data: Name(70%) + Category(30%)
        
        Thresholds:
        - 3 points: Total score ≥ 0.55 (rich) / ≥ 0.60 (basic)
        - 2 points: Total score ≥ 0.35 (rich) / ≥ 0.40 (basic)
        - 1 point: Total score ≥ 0.15 (rich) / ≥ 0.20 (basic)
        - 0 points: Below thresholds
        """
        try:
            # Extract intent categories from question
            intent_analysis = self._extract_intent_categories(question_text)
            
            # Check what data we have available
            has_rich_description = len(result_text.strip()) > 50  # Assume rich if substantial text
            
            # Calculate component scores
            name_score = self._calculate_name_similarity_score(question_text, result_name)
            category_score = self._calculate_category_similarity_score(expected_category, result_text)
            description_score = self._calculate_description_similarity_score(intent_analysis, result_text)
            
            # Apply adaptive weighting based on documented logic
            if has_rich_description:
                # Rich data weighting: Summary(50%) + Description(30%) + Name(15%) + Category(5%)
                # Note: We don't have separate summary, so use description for both
                total_score = (description_score * 0.8 + name_score * 0.15 + category_score * 0.05)
                
                if total_score >= 0.55:
                    return 3
                elif total_score >= 0.35:
                    return 2
                elif total_score >= 0.15:
                    return 1
                else:
                    return 0
            else:
                # Basic data weighting: Name(70%) + Category(30%)
                total_score = (name_score * 0.7 + category_score * 0.3)
                
                if total_score >= 0.60:
                    return 3
                elif total_score >= 0.40:
                    return 2
                elif total_score >= 0.20:
                    return 1
                else:
                    return 0
                    
        except Exception as e:
            print(f"Warning: Error in description scoring: {e}")
            return 0
        
        # Calculate overall score
        if concept_matches >= 2 and (name_relevance or category_relevance):
            return 3  # High semantic + name/category match
        elif concept_matches >= 2:
            return 2  # Good semantic similarity
        elif concept_matches >= 1:
            return 1  # Some semantic similarity
        else:
            return 0  # No relevant similarity
    
    def _score_general_relevance(self, expected_product_name: str, expected_category: str,
                               result_name: str, result_category: str, result_text: str) -> int:
        """General fallback scoring for unknown question types"""
        name_score = 1 if self._check_name_similarity(expected_product_name, result_name) else 0
        category_score = 1 if expected_category == result_category else 0
        
        if name_score > 0 and category_score > 0:
            return 2  # Both name and category match
        elif name_score > 0 or category_score > 0:
            return 1  # Either name or category match
        else:
            return 0  # No matches
    
    def _extract_meaningful_words(self, text: str) -> Set[str]:
        """Extract meaningful words from text, excluding stop words"""
        words = set()
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        for word in clean_text.split():
            if len(word) > 2 and word not in self.stop_words:
                words.add(word)
        
        return words
    
    def _extract_product_names_from_question(self, question_text: str) -> List[str]:
        """Extract potential product names from question using patterns"""
        patterns = [
            r'buying\s+([A-Za-z\s]+?)\s*[-–]',
            r'about\s+(?:the\s+)?([A-Za-z\s]+?)\?',
            r'on\s+([A-Za-z\s]+?)\?',
            r'([A-Za-z\s]+?)\s+compare',
            r"'([A-Za-z\s]+?)'",
            r'"([A-Za-z\s]+?)"',
        ]
        
        product_names = []
        for pattern in patterns:
            matches = re.findall(pattern, question_text, re.IGNORECASE)
            for match in matches:
                clean_match = match.strip()
                if len(clean_match) > 2:
                    product_names.append(clean_match.lower())
        
        return product_names
    
    def _extract_price_ranges_from_question(self, question_text: str) -> List[Tuple[float, float]]:
        """Extract price ranges from question text following documented logic"""
        price_ranges = []
        
        # Pattern for explicit ranges: "$100 to $200", "$100-$200"
        range_patterns = [
            r'\$(\d+(?:\.\d+)?)\s*(?:to|-)\s*\$?(\d+(?:\.\d+)?)',
            r'between\s+\$?(\d+(?:\.\d+)?)\s+and\s+\$?(\d+(?:\.\d+)?)',
        ]
        
        for pattern in range_patterns:
            matches = re.findall(pattern, question_text, re.IGNORECASE)
            for match in matches:
                min_price, max_price = float(match[0]), float(match[1])
                price_ranges.append((min_price, max_price))
        
        # Single price with implied range: "$100" → $80-$120 (±20%)
        single_price_patterns = [
            r'under\s+\$?(\d+(?:\.\d+)?)',
            r'less\s+than\s+\$?(\d+(?:\.\d+)?)',
            r'over\s+\$?(\d+(?:\.\d+)?)',
            r'more\s+than\s+\$?(\d+(?:\.\d+)?)',
            r'around\s+\$?(\d+(?:\.\d+)?)',
            r'\$(\d+(?:\.\d+)?)',
        ]
        
        for pattern in single_price_patterns:
            matches = re.findall(pattern, question_text, re.IGNORECASE)
            for match in matches:
                price = float(match)
                if 'under' in pattern or 'less' in pattern:
                    price_ranges.append((0, price))
                elif 'over' in pattern or 'more' in pattern:
                    price_ranges.append((price, float('inf')))
                else:
                    # Create range with ±20% tolerance
                    tolerance = price * 0.2
                    price_ranges.append((price - tolerance, price + tolerance))
        
        return price_ranges
    
    def _extract_intent_categories(self, question_text: str) -> Dict[str, List[str]]:
        """Extract intent categories following documented logic from SCORING_LOGIC_SUMMARY.md"""
        question_lower = question_text.lower()
        
        # Intent categories with their weighted keywords
        intent_categories = {
            'quality_attributes': {
                'keywords': ['comfort', 'warmth', 'durable', 'lightweight', 'breathable', 'waterproof', 
                           'comfortable', 'warm', 'strong', 'light', 'air', 'water-resistant'],
                'weight': 0.4  # 40% weight
            },
            'functional_features': {
                'keywords': ['performance', 'support', 'stability', 'grip', 'insulation', 'ventilation',
                           'protection', 'cushion', 'flexibility', 'shock', 'impact'],
                'weight': 0.3  # 30% weight
            },
            'use_cases': {
                'keywords': ['outdoor', 'hiking', 'climbing', 'running', 'cycling', 'sports', 'casual',
                           'adventure', 'camping', 'trail', 'exercise', 'fitness'],
                'weight': 0.2  # 20% weight
            },
            'descriptive_terms': {
                'keywords': [],  # Will be filled with other meaningful 3+ character words
                'weight': 0.1  # 10% weight
            }
        }
        
        # Find matches in each category
        found_categories = {}
        for category, data in intent_categories.items():
            matches = []
            for keyword in data['keywords']:
                if keyword in question_lower:
                    matches.append(keyword)
            
            if matches or category == 'descriptive_terms':
                found_categories[category] = {
                    'matches': matches,
                    'weight': data['weight']
                }
        
        # Add descriptive terms (other meaningful words)
        meaningful_words = self._extract_meaningful_words(question_text)
        used_words = set()
        for category_data in found_categories.values():
            used_words.update(category_data['matches'])
        
        descriptive_matches = [word for word in meaningful_words if word not in used_words and len(word) >= 3]
        found_categories['descriptive_terms']['matches'] = descriptive_matches
        
        return found_categories
    
    def _calculate_name_similarity_score(self, question_text: str, result_name: str) -> float:
        """Calculate name similarity score for description questions"""
        if not result_name:
            return 0.0
        
        question_words = self._extract_meaningful_words(question_text)
        result_words = self._extract_meaningful_words(result_name)
        
        if not question_words or not result_words:
            return 0.0
        
        overlap = len(question_words & result_words)
        return overlap / len(question_words)
    
    def _calculate_category_similarity_score(self, expected_category: str, result_text: str) -> float:
        """Calculate category similarity score for description questions"""
        if not expected_category or expected_category == "unknown":
            return 0.0
        
        expected_keywords = self.category_mappings.get(expected_category, [expected_category])
        matches = sum(1 for keyword in expected_keywords if keyword in result_text)
        
        return min(matches / len(expected_keywords), 1.0)
    
    def _calculate_description_similarity_score(self, intent_analysis: Dict, result_text: str) -> float:
        """Calculate description similarity score using intent analysis with documented weighting"""
        total_score = 0.0
        
        for category, data in intent_analysis.items():
            matches = data['matches']
            weight = data['weight']
            
            if matches:
                # Calculate match ratio for this category
                category_matches = sum(1 for match in matches if match in result_text)
                category_score = category_matches / len(matches) if matches else 0.0
                
                # Apply weight
                total_score += category_score * weight
        
        return min(total_score, 1.0)  # Cap at 1.0
    
    def _check_name_similarity(self, expected_name: str, result_name: str) -> bool:
        """Check if names are similar"""
        if not expected_name or not result_name:
            return False
        
        expected_words = self._extract_meaningful_words(expected_name)
        result_words = self._extract_meaningful_words(result_name)
        
        if not expected_words:
            return False
        
        overlap = len(expected_words & result_words)
        return overlap / len(expected_words) >= 0.5
    
    def _check_category_similarity(self, expected_category: str, result_text: str) -> bool:
        """Check if category is similar"""
        if not expected_category or expected_category == "unknown":
            return False
        
        category_keywords = self.category_mappings.get(expected_category, [expected_category])
        return any(keyword in result_text for keyword in category_keywords)
