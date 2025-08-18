#!/usr/bin/env python3
"""
Improved Relevance Scoring Logic for Search Engine Evaluation
Based on the five question types with specific relevance criteria
"""

import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class ImprovedRelevanceScorer:
    """
    Improved relevance scorer that implements specific logic for each question type:
    
    1. Exact word – Result is relevant if it contains the exact word
    2. Category – Result is relevant if it belongs to the same category
    3. Category + Attribute – Result is relevant if same category AND attribute value contains given attribute
    4. Category + Price – Result is relevant if same category AND price falls within specified range
    5. Description – Result is relevant if semantically related to the question
    """
    
    def __init__(self):
        # Define category mappings and synonyms
        self.category_mappings = {
            'clothing': ['clothing', 'apparel', 'wear', 'garment', 'shirt', 'jacket', 'coat', 'sweater'],
            'footwear': ['footwear', 'shoes', 'boots', 'sneakers', 'sandals', 'shoe', 'boot'],
            'bike': ['bike', 'bicycle', 'cycling', 'cycle'],
            'accessory': ['accessory', 'accessories', 'gear', 'equipment'],
            'backpack': ['backpack', 'pack', 'bag', 'rucksack'],
            'helmet': ['helmet', 'head protection'],
            'tent': ['tent', 'shelter', 'camping'],
            'gloves': ['gloves', 'glove', 'hand protection'],
            'shorts_pants': ['shorts', 'pants', 'trousers', 'short', 'pant']
        }
        
        # Common attribute keywords for matching
        self.attribute_keywords = {
            'color': ['color', 'colour', 'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey'],
            'size': ['size', 'small', 'medium', 'large', 'xl', 'xxl', 's', 'm', 'l'],
            'material': ['material', 'cotton', 'polyester', 'wool', 'leather', 'synthetic', 'fabric'],
            'style': ['style', 'casual', 'formal', 'sport', 'athletic', 'outdoor']
        }
    
    def score_result_relevance(self, result: Dict, question_data: Dict) -> int:
        """
        Score a single search result based on improved relevance criteria
        
        Args:
            result: Search result containing product information
            question_data: Original question data with context
            
        Returns:
            Relevance score: 0-3 (0=not relevant, 3=highly relevant)
        """
        question_type = question_data.get('question_type', '').strip()
        question_text = question_data.get('question', '').lower()
        expected_product_name = question_data.get('original_product_name', '').lower()
        expected_category = question_data.get('original_product_category', '').lower()
        expected_price = question_data.get('original_product_price', 0.0)
        expected_attributes = question_data.get('original_product_attributes', [])
        
        # Extract result information
        result_name = result.get('DisplayName', result.get('cr4a3_productname', '')).lower()
        result_category = self._extract_category_from_result(result).lower()
        result_price = self._extract_price_from_result(result)
        result_description = result.get('Description', '').lower()
        result_all_text = f"{result_name} {result_description}".lower()
        
        # Route to specific scoring method based on question type
        if question_type == "Exact word":
            return self._score_exact_word(question_text, expected_product_name, result_name, result_all_text)
        
        elif question_type == "Category":
            return self._score_category(expected_category, result_category, result_all_text)
        
        elif question_type in ["Category + Attribute value", "Attribute value"]:
            return self._score_category_attribute(expected_category, expected_attributes, 
                                                result_category, result_all_text, question_text)
        
        elif question_type in ["Category + Price range", "Price range"]:
            return self._score_category_price(expected_category, expected_price, 
                                            result_category, result_price, question_text, result_all_text)
        
        elif question_type == "Description":
            return self._score_description(question_text, expected_product_name, expected_category,
                                         result_name, result_description, result_all_text)
        
        else:
            # Fallback for unknown question types
            return self._score_general_relevance(expected_product_name, expected_category,
                                               result_name, result_category, result_all_text)
    
    def _score_exact_word(self, question_text: str, expected_product_name: str, 
                         result_name: str, result_all_text: str) -> int:
        """
        Score for "Exact word" questions - result is relevant if it contains the exact word
        
        Improved logic:
        - 3分: 包含产品名字（完整或主要部分）
        - 2分: 包含产品名字的关键部分 + 其他查询词
        - 1分: 包含其他有意义的查询词
        - 0分: 没有相关匹配
        """
        import re
        
        # Extract product names from question using patterns
        product_name_patterns = [
            r'buying\s+([A-Za-z\s]+?)\s*[-–]',  # "buying Product Name -"
            r'about\s+(?:the\s+)?([A-Za-z\s]+?)\?',  # "about the Product Name?"
            r'on\s+([A-Za-z\s]+?)\?',  # "on Product Name?"
            r'([A-Za-z\s]+?)\s+compare',  # "Product Name compare"
            r"'([A-Za-z\s]+?)'",  # 'Product Name'
            r'"([A-Za-z\s]+?)"',  # "Product Name"
        ]
        
        query_product_names = set()
        for pattern in product_name_patterns:
            matches = re.findall(pattern, question_text, re.IGNORECASE)
            for match in matches:
                clean_match = match.strip()
                if len(clean_match) > 2:  # Filter out too short matches
                    query_product_names.add(clean_match.lower())
        
        # Extract meaningful query words (excluding stop words)
        stop_words = {
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
            'buying', 'worth', 'tell', 'heard'
        }
        
        query_words = set()
        clean_question = re.sub(r'[^\w\s]', ' ', question_text.lower())
        for word in clean_question.split():
            if len(word) > 2 and word not in stop_words:
                query_words.add(word)
        
        result_name_lower = result_name.lower()
        result_all_lower = result_all_text.lower()
        
        # Check product name coverage
        best_product_coverage = 0
        for query_name in query_product_names:
            query_name_words = set(query_name.split())
            result_name_words = set(result_name_lower.split())
            
            if query_name_words and result_name_words:
                common_words = query_name_words.intersection(result_name_words)
                coverage = len(common_words) / len(query_name_words)
                best_product_coverage = max(best_product_coverage, coverage)
        
        # Check query word coverage
        result_text_words = set(re.findall(r'\w+', result_all_lower))
        query_word_matches = query_words.intersection(result_text_words)
        query_word_coverage = len(query_word_matches) / len(query_words) if query_words else 0
        
        # Scoring logic
        if best_product_coverage >= 0.7:
            return 3  # 包含产品名字（>=70%的字符匹配）
        elif best_product_coverage >= 0.3 and query_word_coverage >= 0.3:
            return 2  # 部分产品名字 + 其他有意义的查询词
        elif query_word_coverage >= 0.3:
            return 1  # 其他有意义的查询词但不包含产品名字
        else:
            return 0  # 无相关内容
    
    def _score_category(self, expected_category: str, result_category: str, result_all_text: str) -> int:
        """
        Score for "Category" questions - result is relevant if it belongs to the same category
        """
        if not expected_category:
            return 0
        
        # Direct category match
        if expected_category == result_category:
            return 3
        
        # Check category synonyms and mappings
        expected_keywords = self.category_mappings.get(expected_category, [expected_category])
        result_keywords = self.category_mappings.get(result_category, [result_category])
        
        # Check for category keyword matches
        category_matches = 0
        for exp_keyword in expected_keywords:
            if exp_keyword in result_all_text:
                category_matches += 1
        
        for res_keyword in result_keywords:
            if any(exp_keyword in res_keyword or res_keyword in exp_keyword 
                   for exp_keyword in expected_keywords):
                category_matches += 2  # Higher weight for direct category mapping
        
        # Scoring logic
        if category_matches >= 2:
            return 2  # Strong category match
        elif category_matches >= 1:
            return 1  # Weak category match
        else:
            return 0  # No category match
    
    def _score_category_attribute(self, expected_category: str, expected_attributes: List[Dict],
                                result_category: str, result_all_text: str, question_text: str) -> int:
        """
        Score for "Category + Attribute value" questions
        Result is relevant if same category AND attribute value contains given attribute
        """
        # First check category relevance
        category_score = self._score_category(expected_category, result_category, result_all_text)
        
        if category_score == 0:
            return 0  # Must match category first
        
        # Extract attribute values from question and expected attributes
        attribute_values = []
        
        # From expected attributes
        for attr in expected_attributes:
            if isinstance(attr, dict) and 'value' in attr:
                attribute_values.append(attr['value'].lower())
        
        # From question text (extract potential attribute values)
        question_attributes = self._extract_attributes_from_question(question_text)
        attribute_values.extend(question_attributes)
        
        if not attribute_values:
            return category_score  # If no attributes to match, return category score
        
        # Check for attribute matches in result
        attribute_matches = 0
        for attr_value in attribute_values:
            if attr_value in result_all_text:
                attribute_matches += 1
        
        # Combined scoring
        if attribute_matches >= len(attribute_values) and category_score >= 2:
            return 3  # Perfect match: correct category + all attributes
        elif attribute_matches > 0 and category_score >= 2:
            return 2  # Good match: correct category + some attributes
        elif attribute_matches > 0:
            return 1  # Partial match: attributes found but weak category
        else:
            return max(0, category_score - 1)  # Category match but no attributes
    
    def _score_category_price(self, expected_category: str, expected_price: float,
                            result_category: str, result_price: float, question_text: str, result_all_text: str) -> int:
        """
        Score for "Category + Price range" questions
        Result is relevant if same category AND price falls within specified range
        """
        # First check category relevance
        category_score = self._score_category(expected_category, result_category, result_all_text)
        
        if category_score == 0:
            return 0  # Must match category first
        
        # Extract price range from question
        price_range = self._extract_price_range_from_question(question_text, expected_price)
        
        if not price_range or result_price <= 0:
            return category_score  # If no price info, return category score
        
        min_price, max_price = price_range
        
        # Check if result price is within range
        price_match = min_price <= result_price <= max_price
        
        # Combined scoring
        if price_match and category_score >= 2:
            return 3  # Perfect match: correct category + price in range
        elif price_match:
            return 2  # Good match: price in range but weak category
        elif category_score >= 2:
            return 1  # Category match but price outside range
        else:
            return 0  # Neither category nor price match well
    
    def _score_description(self, question_text: str, expected_product_name: str, expected_category: str,
                          result_name: str, result_description: str, result_all_text: str) -> int:
        """
        Score for "Description" questions - check if summary semantically matches what question is asking
        
        For Description questions, we prioritize:
        1. Summary explanation matching the question intent
        2. Product description matching question keywords  
        3. Product name containing relevant terms
        4. Category relevance (enhanced for cases with limited description data)
        """
        # Extract key intent from question (what user is looking for)
        question_intent = self._extract_question_intent(question_text)
        
        # Try to get summary from result if available
        result_summary = ""
        actual_description = ""
        
        if isinstance(result_description, dict):
            result_summary = result_description.get('summary', '')
            actual_description = result_description.get('description', '')
        elif isinstance(result_description, str):
            actual_description = result_description
        
        # Check if we have meaningful description data
        has_description_data = bool(result_summary or actual_description)
        
        # Calculate different types of semantic matches
        summary_match = 0
        description_match = 0
        name_match = 0
        category_relevance = 0
        
        # 1. Summary semantic matching (highest priority for Description questions)
        if result_summary:
            summary_match = self._calculate_description_semantic_match(question_intent, result_summary)
        
        # 2. Product description matching
        if actual_description:
            description_match = self._calculate_description_semantic_match(question_intent, actual_description)
        
        # 3. Enhanced product name matching (include category keywords)
        name_match = self._calculate_enhanced_name_match(question_intent, result_name, expected_category, result_all_text)
        
        # 4. Enhanced category relevance (more important when description data is missing)
        if expected_category:
            expected_keywords = self.category_mappings.get(expected_category, [expected_category])
            for keyword in expected_keywords:
                if keyword.lower() in result_all_text.lower():
                    category_relevance += 1
        
        # Adaptive weighted scoring for Description questions
        if has_description_data:
            # When we have description data, use original weights
            summary_weight = 0.5
            description_weight = 0.3
            name_weight = 0.15
            category_weight = 0.05
        else:
            # When no description data, increase name and category weights
            summary_weight = 0.0
            description_weight = 0.0
            name_weight = 0.7   # Increased from 0.15
            category_weight = 0.3  # Increased from 0.05
        
        total_score = (
            summary_match * summary_weight +
            description_match * description_weight +
            name_match * name_weight +
            min(category_relevance, 1.0) * category_weight
        )
        
        # Adjusted thresholds for Description questions
        if has_description_data:
            # Original thresholds when we have rich description data
            if total_score >= 0.55:
                return 3  
            elif total_score >= 0.35:
                return 2  
            elif total_score >= 0.15:
                return 1  
            else:
                return 0
        else:
            # More lenient thresholds when only name/category data is available
            if total_score >= 0.6:   # Strong name + category match
                return 3  
            elif total_score >= 0.4:  # Good name + category match
                return 2  
            elif total_score >= 0.2:  # Basic name or category match
                return 1  
            else:
                return 0
    
    def _extract_question_intent(self, question_text: str) -> Dict[str, List[str]]:
        """
        Extract the intent and key descriptive terms from a description question
        
        Returns:
            Dictionary with intent categories and associated keywords
        """
        question_lower = question_text.lower()
        
        intent = {
            'quality_attributes': [],
            'functional_features': [],
            'use_cases': [],
            'descriptive_terms': []
        }
        
        # Quality attributes (comfort, warmth, durability, etc.)
        quality_terms = [
            'comfort', 'comfortable', 'warmth', 'warm', 'durable', 'durability',
            'lightweight', 'breathable', 'waterproof', 'versatile', 'quality',
            'protection', 'protective', 'adjustable', 'flexible', 'soft', 'strong'
        ]
        
        # Functional features
        functional_terms = [
            'performance', 'support', 'stability', 'grip', 'traction', 'insulation',
            'ventilation', 'moisture-wicking', 'quick-dry', 'stretch', 'reinforced'
        ]
        
        # Use cases and contexts
        use_case_terms = [
            'outdoor', 'hiking', 'climbing', 'running', 'cycling', 'sports',
            'casual', 'professional', 'travel', 'adventure', 'weather', 'rain'
        ]
        
        # Extract quality attributes
        for term in quality_terms:
            if term in question_lower:
                intent['quality_attributes'].append(term)
        
        # Extract functional features
        for term in functional_terms:
            if term in question_lower:
                intent['functional_features'].append(term)
        
        # Extract use cases
        for term in use_case_terms:
            if term in question_lower:
                intent['use_cases'].append(term)
        
        # Extract other descriptive terms (3+ character words, excluding common words)
        import re
        stop_words = {
            'the', 'and', 'for', 'with', 'are', 'you', 'can', 'find', 'show', 'get', 
            'want', 'need', 'that', 'have', 'has', 'any', 'looking', 'recommend',
            'suggestions', 'offers', 'provides', 'what', 'which', 'how'
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', question_lower)
        for word in words:
            if (word not in stop_words and 
                word not in intent['quality_attributes'] and 
                word not in intent['functional_features'] and 
                word not in intent['use_cases']):
                intent['descriptive_terms'].append(word)
        
        return intent
    
    def _calculate_description_semantic_match(self, question_intent: Dict[str, List[str]], text: str) -> float:
        """
        Calculate semantic match between question intent and result text
        
        Args:
            question_intent: Extracted intent from question
            text: Text to match against (summary, description, or name)
            
        Returns:
            Semantic match score (0.0 to 1.0)
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        total_matches = 0
        total_terms = 0
        
        # Weight different types of matches
        weights = {
            'quality_attributes': 0.4,  # Highest weight for quality attributes
            'functional_features': 0.3,
            'use_cases': 0.2,
            'descriptive_terms': 0.1
        }
        
        for category, terms in question_intent.items():
            if not terms:
                continue
                
            category_matches = 0
            for term in terms:
                # Direct match
                if term in text_lower:
                    category_matches += 1
                # Partial match (for compound words)
                elif any(part in text_lower for part in term.split() if len(part) > 2):
                    category_matches += 0.5
                # Synonym match for important terms
                elif category == 'quality_attributes':
                    synonyms = self._get_quality_synonyms(term)
                    if any(syn in text_lower for syn in synonyms):
                        category_matches += 0.8
            
            if terms:
                category_score = category_matches / len(terms)
                total_matches += category_score * weights[category]
                total_terms += weights[category]
        
        return total_matches / total_terms if total_terms > 0 else 0.0
    
    def _calculate_enhanced_name_match(self, question_intent: Dict[str, List[str]], 
                                     result_name: str, expected_category: str, result_all_text: str) -> float:
        """
        Enhanced name matching that includes category keyword matching for Description questions
        
        Args:
            question_intent: Extracted intent from question
            result_name: Product name to match against
            expected_category: Expected product category
            result_all_text: All result text for additional matching
            
        Returns:
            Enhanced semantic match score (0.0 to 1.0)
        """
        # Start with basic semantic matching
        base_match = self._calculate_description_semantic_match(question_intent, result_name)
        
        # Add category keyword matching bonus
        category_bonus = 0.0
        if expected_category:
            expected_keywords = self.category_mappings.get(expected_category, [expected_category])
            category_matches = 0
            
            for keyword in expected_keywords:
                if keyword.lower() in result_name.lower():
                    category_matches += 1
            
            # Calculate category bonus (up to 0.5 additional score)
            if category_matches > 0:
                category_bonus = min(0.5, category_matches * 0.2)
        
        # Add descriptive terms matching bonus
        descriptive_bonus = 0.0
        descriptive_terms = question_intent.get('descriptive_terms', [])
        
        for term in descriptive_terms:
            # Check if any category keywords match the descriptive term intent
            if expected_category:
                category_keywords = self.category_mappings.get(expected_category, [])
                for cat_keyword in category_keywords:
                    if cat_keyword.lower() in result_name.lower():
                        # If the result contains a category keyword that relates to the descriptive term
                        if (term == 'footwear' and cat_keyword in ['shoes', 'boots', 'shoe', 'boot']) or \
                           (term == 'clothing' and cat_keyword in ['shirt', 'jacket', 'coat']) or \
                           (term == 'bike' and cat_keyword in ['bicycle', 'cycling']):
                            descriptive_bonus += 0.3
                            break
        
        # Combine scores (cap at 1.0)
        total_score = min(1.0, base_match + category_bonus + descriptive_bonus)
        return total_score
    
    def _get_quality_synonyms(self, term: str) -> List[str]:
        """Get synonyms for quality attribute terms"""
        synonym_map = {
            'comfort': ['comfortable', 'cozy', 'soft', 'cushioned', 'padded'],
            'warmth': ['warm', 'insulated', 'thermal', 'heat-retaining'],
            'durable': ['durability', 'tough', 'strong', 'long-lasting', 'robust'],
            'lightweight': ['light', 'compact', 'portable'],
            'breathable': ['ventilated', 'airy', 'moisture-wicking'],
            'waterproof': ['water-resistant', 'weatherproof', 'sealed'],
            'versatile': ['adaptable', 'multi-purpose', 'flexible'],
            'protection': ['protective', 'shielding', 'safety'],
            'quality': ['premium', 'high-grade', 'superior', 'excellent']
        }
        
        return synonym_map.get(term, [])
    
    def _score_general_relevance(self, expected_product_name: str, expected_category: str,
                               result_name: str, result_category: str, result_all_text: str) -> int:
        """
        Fallback scoring for unknown question types
        """
        # Check for name similarity
        name_similarity = self._calculate_text_similarity(expected_product_name, result_name)
        
        # Check for category match
        category_match = expected_category == result_category if expected_category else False
        
        if name_similarity >= 0.8:
            return 3
        elif name_similarity >= 0.5 or category_match:
            return 2
        elif name_similarity >= 0.2:
            return 1
        else:
            return 0
    
    # Helper methods
    
    def _extract_key_words(self, question_text: str, expected_product_name: str) -> List[str]:
        """Extract key words from question and product name"""
        key_words = []
        
        # From product name
        if expected_product_name:
            words = [w.strip() for w in expected_product_name.split() if len(w.strip()) > 2]
            key_words.extend(words)
        
        # From question (extract meaningful words)
        question_words = re.findall(r'\b[a-zA-Z]{3,}\b', question_text.lower())
        # Filter out common words
        stop_words = {'the', 'and', 'for', 'with', 'are', 'you', 'can', 'find', 'show', 'get', 'want', 'need'}
        meaningful_words = [w for w in question_words if w not in stop_words]
        key_words.extend(meaningful_words)
        
        return list(set(key_words))  # Remove duplicates
    
    def _extract_category_from_result(self, result: Dict) -> str:
        """Extract category from result, checking multiple possible fields"""
        category_fields = ['Category', 'category', 'CategoryName', 'product_category']
        
        for field in category_fields:
            if field in result and result[field]:
                return str(result[field]).strip()
        
        return ""
    
    def _extract_price_from_result(self, result: Dict) -> float:
        """Extract price from result, checking multiple possible fields"""
        price_fields = ['Price', 'price', 'ListPrice', 'BasePrice']
        
        for field in price_fields:
            if field in result and result[field]:
                try:
                    return float(result[field])
                except (ValueError, TypeError):
                    continue
        
        return 0.0
    
    def _extract_attributes_from_question(self, question_text: str) -> List[str]:
        """Extract attribute values from question text"""
        attributes = []
        
        # Look for color mentions
        for color in self.attribute_keywords['color']:
            if color in question_text:
                attributes.append(color)
        
        # Look for size mentions
        for size in self.attribute_keywords['size']:
            if size in question_text:
                attributes.append(size)
        
        # Look for material mentions
        for material in self.attribute_keywords['material']:
            if material in question_text:
                attributes.append(material)
        
        return attributes
    
    def _extract_price_range_from_question(self, question_text: str, expected_price: float) -> Tuple[float, float]:
        """Extract price range from question text"""
        # Look for explicit price ranges
        price_pattern = r'\$?(\d+(?:\.\d{2})?)\s*(?:to|-)?\s*\$?(\d+(?:\.\d{2})?)?'
        matches = re.findall(price_pattern, question_text)
        
        if matches:
            prices = []
            for match in matches:
                try:
                    if match[0]:
                        prices.append(float(match[0]))
                    if match[1]:
                        prices.append(float(match[1]))
                except ValueError:
                    continue
            
            if len(prices) >= 2:
                return (min(prices), max(prices))
            elif len(prices) == 1:
                # Single price mentioned - create range around it
                price = prices[0]
                return (price * 0.8, price * 1.2)
        
        # If no explicit range, use expected price with tolerance
        if expected_price > 0:
            return (expected_price * 0.7, expected_price * 1.3)
        
        return None
    
    def _extract_semantic_concepts(self, text: str) -> List[str]:
        """Extract semantic concepts from text"""
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'and', 'for', 'with', 'are', 'you', 'can', 'find', 'show', 'get', 'want', 'need', 'that', 'have', 'has'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        concepts = [w for w in words if w not in stop_words]
        return concepts
    
    def _calculate_semantic_similarity(self, concepts: List[str], text: str) -> float:
        """Calculate semantic similarity between concepts and text"""
        if not concepts or not text:
            return 0.0
        
        text_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))
        concept_set = set(concepts)
        
        # Calculate intersection over union
        intersection = concept_set.intersection(text_words)
        union = concept_set.union(text_words)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using common words"""
        if not text1 or not text2:
            return 0.0
            
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

def test_improved_scorer():
    """Test the improved relevance scorer"""
    scorer = ImprovedRelevanceScorer()
    
    # Test cases for different question types
    test_cases = [
        {
            'question_data': {
                'question': 'find me boots',
                'question_type': 'Exact word',
                'original_product_name': 'hiking boots',
                'original_product_category': 'footwear'
            },
            'results': [
                {'DisplayName': 'Alpine Hiking Boots', 'Category': 'footwear', 'Description': 'Waterproof hiking boots'},
                {'DisplayName': 'Running Shoes', 'Category': 'footwear', 'Description': 'Lightweight running shoes'},
                {'DisplayName': 'Hiking Jacket', 'Category': 'clothing', 'Description': 'Outdoor jacket for hiking'}
            ]
        },
        {
            'question_data': {
                'question': 'show me footwear products',
                'question_type': 'Category',
                'original_product_category': 'footwear'
            },
            'results': [
                {'DisplayName': 'Alpine Hiking Boots', 'Category': 'footwear', 'Description': 'Waterproof hiking boots'},
                {'DisplayName': 'Running Shoes', 'Category': 'footwear', 'Description': 'Lightweight running shoes'},
                {'DisplayName': 'Hiking Jacket', 'Category': 'clothing', 'Description': 'Outdoor jacket for hiking'}
            ]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['question_data']['question_type']}")
        print(f"Question: {test_case['question_data']['question']}")
        print("Results and Scores:")
        
        for j, result in enumerate(test_case['results']):
            score = scorer.score_result_relevance(result, test_case['question_data'])
            print(f"  {j+1}. {result['DisplayName']} (Category: {result['Category']}) -> Score: {score}")

if __name__ == "__main__":
    test_improved_scorer()
