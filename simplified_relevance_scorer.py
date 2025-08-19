#!/usr/bin/env python3
"""
Simplified Relevance Scoring Logic based on clear 100% relevance criteria
"""

import re
import json
from typing import Dict, List, Set, Tuple, Any, Union
from collections import defaultdict

class SimplifiedRelevanceScorer:
    """
    Simplified relevance scorer with clear 100% relevance criteria:
    
    Scoring Scale (0-1):
    - 1.0: 100% relevant (meets specific criteria)
    - 0.67: Partially relevant 
    - 0.33: Somewhat relevant
    - 0.0: Not relevant
    
    100% Relevance Criteria:
    1. Exact word – Result contains the product name → 1.0
    2. Description – Result contains key words from description → 1.0
    3. Category – Result category matches original product category → 1.0
    4. Category + Price – Result category matches AND price in question range → 1.0
    5. Category + Attribute – Result category matches AND contains mentioned attributes → 1.0
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
        Score a single search result based on simplified 100% relevance criteria
        
        Args:
            result: Search result (Dict for dataverse, str for agentic parsed product)
            question_data: Original question data with context
            result_format: 'dataverse' or 'agentic' to handle different formats
            
        Returns:
            Relevance score: 0, 1, 2, or 3 (will be converted to 0.0, 0.33, 0.67, 1.0)
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
                return self._score_exact_word_simplified(expected_product_name, result_name, result_text)
            
            elif question_type == "Category":
                return self._score_category_simplified(expected_category, result_category, result_text)
            
            elif question_type in ["Category + Attribute value", "Attribute value"]:
                return self._score_category_attribute_simplified(expected_category, expected_attributes, 
                                                    result_category, result_text, question_text)
            
            elif question_type in ["Category + Price range", "Price range"]:
                return self._score_category_price_simplified(expected_category, expected_price, 
                                                result_category, result_price, question_text, result_text)
            
            elif question_type == "Description":
                return self._score_description_simplified(question_text, result_text)
            
            else:
                # Fallback for unknown question types
                return self._score_general_relevance(expected_product_name, expected_category,
                                                   result_name, result_category, result_text)
        
        except Exception as e:
            print(f"⚠️ Error scoring relevance: {e}")
            return 0
    
    def _score_exact_word_simplified(self, expected_product_name: str, result_name: str, result_text: str) -> int:
        """
        Exact word scoring: 100% relevant if result contains the product name
        """
        if not expected_product_name:
            return 0
        
        # Check if product name (or key parts) appears in result
        product_words = set(expected_product_name.split())
        result_words = set(result_text.split())
        
        # If most of the product name words are found → 100% relevant
        if product_words and len(product_words & result_words) >= len(product_words) * 0.7:
            return 3  # 100% relevant
        
        # If some product name words are found → partially relevant
        if product_words and len(product_words & result_words) >= len(product_words) * 0.3:
            return 2  # 67% relevant
        
        # Check for any meaningful word overlap
        meaningful_overlap = len(product_words & result_words)
        if meaningful_overlap > 0:
            return 1  # 33% relevant
        
        return 0  # Not relevant
    
    def _score_category_simplified(self, expected_category: str, result_category: str, result_text: str) -> int:
        """
        Category scoring: 100% relevant if result category matches original product category
        """
        if not expected_category:
            return 0
        
        # Direct category match → 100% relevant
        if expected_category == result_category and expected_category != "unknown":
            return 3
        
        # Check category keywords in result text
        expected_keywords = self.category_mappings.get(expected_category, [expected_category])
        found_keywords = 0
        
        for keyword in expected_keywords:
            if keyword in result_text:
                found_keywords += 1
        
        # If main category keyword found → 100% relevant
        if expected_category in result_text or found_keywords >= 2:
            return 3  # 100% relevant
        
        # If some category keywords found → partially relevant
        if found_keywords >= 1:
            return 2  # 67% relevant
        
        return 0  # Not relevant
    
    def _score_category_attribute_simplified(self, expected_category: str, expected_attributes: List[Dict],
                                result_category: str, result_text: str, question_text: str) -> int:
        """
        Category + Attribute scoring: 100% relevant if category matches AND contains mentioned attributes
        """
        # First check category match
        category_score = self._score_category_simplified(expected_category, result_category, result_text)
        
        if category_score == 0:
            return 0  # Must have category relevance first
        
        # Extract attribute values to check
        attributes_to_check = []
        
        # From expected attributes
        for attr in expected_attributes:
            if isinstance(attr, dict):
                attr_value = attr.get('value', attr.get('Value', ''))
                if attr_value:
                    attributes_to_check.append(attr_value.lower())
        
        # From question text (extract attribute mentions)
        question_attributes = self._extract_attributes_from_question(question_text)
        attributes_to_check.extend(question_attributes)
        
        if not attributes_to_check:
            return category_score  # Return category score if no attributes to check
        
        # Check for attribute matches in result
        attribute_matches = 0
        for attr_value in attributes_to_check:
            if attr_value in result_text:
                attribute_matches += 1
        
        # If category matches AND all/most attributes found → 100% relevant
        if category_score >= 3 and attribute_matches >= len(attributes_to_check) * 0.8:
            return 3  # 100% relevant
        
        # If category matches AND some attributes found → partially relevant
        if category_score >= 3 and attribute_matches > 0:
            return 2  # 67% relevant
        
        # If only category matches → return category score
        return min(category_score, 2)
    
    def _score_category_price_simplified(self, expected_category: str, expected_price: float,
                            result_category: str, result_price: float, 
                            question_text: str, result_text: str) -> int:
        """
        Category + Price scoring: 100% relevant if category matches AND price in question range
        """
        # First check category match
        category_score = self._score_category_simplified(expected_category, result_category, result_text)
        
        if category_score == 0:
            return 0  # Must have category relevance first
        
        # Extract price range from question
        price_ranges = self._extract_price_ranges_from_question(question_text)
        
        if not price_ranges and expected_price <= 0:
            return category_score  # Return category score if no price info
        
        # Check if result price is within any of the ranges
        price_in_range = False
        
        if price_ranges:
            for min_price, max_price in price_ranges:
                if min_price <= result_price <= max_price:
                    price_in_range = True
                    break
        else:
            # Use expected price with tolerance if no ranges found
            if expected_price > 0:
                tolerance = expected_price * 0.2  # ±20% tolerance
                if abs(result_price - expected_price) <= tolerance:
                    price_in_range = True
        
        # If category matches AND price in range → 100% relevant
        if category_score >= 3 and price_in_range:
            return 3  # 100% relevant
        
        # If category matches but price not in range → category score only
        if category_score >= 3:
            return 2  # 67% relevant
        
        # If price matches but weak category → partial relevance
        if price_in_range:
            return 2  # 67% relevant
        
        return min(category_score, 1)
    
    def _score_description_simplified(self, question_text: str, result_text: str) -> int:
        """
        Description scoring: 100% relevant if result contains key words from description
        """
        # Extract meaningful words from question (excluding stop words)
        question_words = self._extract_meaningful_words(question_text)
        result_words = self._extract_meaningful_words(result_text)
        
        if not question_words:
            return 0
        
        # Calculate word overlap
        word_overlap = len(question_words & result_words)
        overlap_ratio = word_overlap / len(question_words)
        
        # If most key words found → 100% relevant
        if overlap_ratio >= 0.6:
            return 3  # 100% relevant
        
        # If some key words found → partially relevant
        if overlap_ratio >= 0.3:
            return 2  # 67% relevant
        
        # If few key words found → somewhat relevant
        if overlap_ratio >= 0.1:
            return 1  # 33% relevant
        
        return 0  # Not relevant
    
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
    
    def _extract_meaningful_words(self, text: str) -> Set[str]:
        """Extract meaningful words from text, excluding stop words"""
        words = set()
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        for word in clean_text.split():
            if len(word) > 2 and word not in self.stop_words:
                words.add(word)
        
        return words
    
    def _extract_attributes_from_question(self, question_text: str) -> List[str]:
        """Extract attribute values from question text"""
        attributes = []
        question_lower = question_text.lower()
        
        # Look for color mentions
        for color in self.attribute_keywords['color']:
            if color in question_lower:
                attributes.append(color)
        
        # Look for size mentions
        for size in self.attribute_keywords['size']:
            if size in question_lower:
                attributes.append(size)
        
        # Look for material mentions
        for material in self.attribute_keywords['material']:
            if material in question_lower:
                attributes.append(material)
        
        # Look for style mentions
        for style in self.attribute_keywords['style']:
            if style in question_lower:
                attributes.append(style)
        
        # Look for features mentions
        for feature in self.attribute_keywords['features']:
            if feature in question_lower:
                attributes.append(feature)
        
        return attributes
    
    def _extract_price_ranges_from_question(self, question_text: str) -> List[Tuple[float, float]]:
        """Extract price ranges from question text"""
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
        
        # Single price with implied range: "under $50" → $0-$50
        single_price_patterns = [
            (r'under\s+\$?(\d+(?:\.\d+)?)', 'under'),
            (r'less\s+than\s+\$?(\d+(?:\.\d+)?)', 'under'),
            (r'over\s+\$?(\d+(?:\.\d+)?)', 'over'),
            (r'more\s+than\s+\$?(\d+(?:\.\d+)?)', 'over'),
            (r'around\s+\$?(\d+(?:\.\d+)?)', 'around'),
            (r'\$(\d+(?:\.\d+)?)', 'exact'),
        ]
        
        for pattern, price_type in single_price_patterns:
            matches = re.findall(pattern, question_text, re.IGNORECASE)
            for match in matches:
                price = float(match)
                if price_type in ['under', 'less']:
                    price_ranges.append((0, price))
                elif price_type in ['over', 'more']:
                    price_ranges.append((price, float('inf')))
                elif price_type == 'around':
                    # Create range with ±20% tolerance
                    tolerance = price * 0.2
                    price_ranges.append((price - tolerance, price + tolerance))
                else:  # exact
                    # Create range with ±10% tolerance for exact price
                    tolerance = price * 0.1
                    price_ranges.append((price - tolerance, price + tolerance))
        
        return price_ranges
    
    def _score_general_relevance(self, expected_product_name: str, expected_category: str,
                               result_name: str, result_category: str, result_text: str) -> int:
        """General fallback scoring for unknown question types"""
        name_score = 0
        category_score = 0
        
        # Check name similarity
        if expected_product_name:
            expected_words = set(expected_product_name.split())
            result_words = set(result_text.split())
            if expected_words and len(expected_words & result_words) >= len(expected_words) * 0.5:
                name_score = 2
            elif len(expected_words & result_words) > 0:
                name_score = 1
        
        # Check category match
        if expected_category == result_category and expected_category != "unknown":
            category_score = 2
        elif expected_category:
            expected_keywords = self.category_mappings.get(expected_category, [expected_category])
            if any(keyword in result_text for keyword in expected_keywords):
                category_score = 1
        
        return min(3, name_score + category_score)
