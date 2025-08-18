# Search Results Scoring Logic Summary

## Overview

This document summarizes the relevance scoring logic for two search systems implemented in the retail RAG web application:

1. **Dataverse Search** - Traditional structured search using `analyze_search_results.py`
2. **Agentic Search** - AI-powered search using `analyze_agentic_search_results.py`

Both systems use the same underlying `ImprovedRelevanceScorer` class with question-type specific scoring logic.

## Shared Scoring Framework

### Question Types

Both search systems evaluate results based on 5 distinct question types:

1. **Exact word** - Result is relevant if it contains the exact word/product name
2. **Category** - Result is relevant if it belongs to the same category  
3. **Category + Attribute** - Result is relevant if same category AND attribute value matches
4. **Category + Price** - Result is relevant if same category AND price falls within range
5. **Description** - Result is relevant if semantically related to the question

### Scoring Scale

All scoring uses a 4-point scale:
- **0 points**: Not relevant
- **1 point**: Weakly relevant 
- **2 points**: Relevant (threshold for inclusion in metrics)
- **3 points**: Highly relevant/exact match

## Detailed Scoring Logic by Question Type

### 1. Exact Word Questions

**Purpose**: Find products that contain specific product names or exact terms mentioned in the query.

**Example**: "I'm considering buying Yint Mug - is it worth it?"

**Scoring Logic**:

```
3 points: Product name coverage ≥ 70%
  - Query contains "Yint Mug", result contains "Yint Mug" = 100% coverage → 3 points
  
2 points: Partial product name (≥30%) + meaningful query words (≥30%)
  - Query contains "Yint Mug", result contains "Coffee Mug" = 50% coverage + "mug" match → 2 points
  
1 point: Meaningful query words only (≥30% coverage)
  - Query contains meaningful words that appear in result description → 1 point
  
0 points: No significant matches
```

**Key Features**:
- Extracts product names using regex patterns (`buying Product Name -`, `about Product Name?`, etc.)
- Filters out stop words (common words like "the", "and", "is", etc.)
- Calculates word-level coverage for product names
- Considers both exact matches and partial matches

### 2. Category Questions

**Purpose**: Find products that belong to the same category as requested.

**Example**: "Show me footwear products"

**Scoring Logic**:

```
3 points: Direct category match
  - Expected: "footwear", Result: "footwear" → 3 points
  
2 points: Strong category match via synonyms/mappings
  - Expected: "footwear", Result contains "shoes", "boots" → 2 points
  
1 point: Weak category match
  - Some category-related keywords found → 1 point
  
0 points: No category relevance
```

**Category Mappings**:
```
clothing: ['clothing', 'apparel', 'wear', 'garment', 'shirt', 'jacket', 'coat']
footwear: ['footwear', 'shoes', 'boots', 'sneakers', 'sandals']
bike: ['bike', 'bicycle', 'cycling', 'cycle']
accessory: ['accessory', 'accessories', 'gear', 'equipment']
backpack: ['backpack', 'pack', 'bag', 'rucksack']
```

### 3. Category + Attribute Questions

**Purpose**: Find products matching both category and specific attribute values.

**Example**: "Find red clothing items"

**Scoring Logic**:

```
3 points: Perfect match (correct category + all attributes)
  - Category match + all attribute values found → 3 points
  
2 points: Good match (correct category + some attributes)
  - Strong category match + partial attribute matches → 2 points
  
1 point: Partial match (attributes found but weak category)
  - Some attributes match but category is weak → 1 point
  
0 points: Poor category match or no attributes
```

**Attribute Detection**:
- Color: ['black', 'white', 'red', 'blue', 'green', 'yellow', etc.]
- Size: ['small', 'medium', 'large', 'xl', 'xxl', 's', 'm', 'l']
- Material: ['cotton', 'polyester', 'wool', 'leather', 'synthetic']
- Style: ['casual', 'formal', 'sport', 'athletic', 'outdoor']

### 4. Category + Price Questions

**Purpose**: Find products matching category within a specific price range.

**Example**: "Show me bikes under $500"

**Scoring Logic**:

```
3 points: Perfect match (correct category + price in range)
  - Category match + price within extracted range → 3 points
  
2 points: Price match but weak category OR strong category but price outside range
  - Good price match OR good category match → 2 points
  
1 point: Category match but price outside range
  - Category is relevant but price doesn't match → 1 point
  
0 points: Neither category nor price match well
```

**Price Range Extraction**:
- Looks for explicit ranges: "$100 to $200", "$100-$200"
- Single price creates range: "$100" → $80-$120 (±20%)
- Uses expected price with tolerance: ±30% if no explicit range

### 5. Description Questions

**Purpose**: Find products that semantically match the descriptive intent of the question.

**Example**: "What outdoor gear offers the best protection from weather?"

**Scoring Logic**:

This is the most complex scoring type with adaptive weighting based on available data:

**When rich description data is available**:
```
Weights: Summary(50%) + Description(30%) + Name(15%) + Category(5%)

3 points: Total score ≥ 0.55
2 points: Total score ≥ 0.35  
1 point: Total score ≥ 0.15
0 points: Total score < 0.15
```

**When only basic data is available** (no summary/description):
```
Weights: Name(70%) + Category(30%)

3 points: Total score ≥ 0.60
2 points: Total score ≥ 0.40
1 point: Total score ≥ 0.20
0 points: Total score < 0.20
```

**Intent Extraction Categories**:
- **Quality Attributes**: comfort, warmth, durable, lightweight, breathable, waterproof
- **Functional Features**: performance, support, stability, grip, insulation, ventilation
- **Use Cases**: outdoor, hiking, climbing, running, cycling, sports, casual
- **Descriptive Terms**: Other meaningful 3+ character words

**Semantic Matching**:
- Quality attributes get highest weight (40%)
- Functional features get 30% weight
- Use cases get 20% weight
- Other descriptive terms get 10% weight
- Includes synonym matching for quality terms

## Search System Differences

### Dataverse Search (`analyze_search_results.py`)

**Data Structure**:
- Uses structured Dataverse API responses
- Product fields: `DisplayName`, `Category`, `Price`, `Description`
- Simpler result extraction from `queryResult.result` array

**Key Features**:
- Direct field access from structured data
- Consistent data format across all results
- Traditional search result ranking

### Agentic Search (`analyze_agentic_search_results.py`)

**Data Structure**:
- Uses AI-generated responses in `FormattedText` field
- Requires JSON parsing of AI response
- Product extraction via regex patterns from content strings

**Key Features**:
- **Enhanced Error Handling**:
  ```python
  # Checks for throttling and execution errors
  def _is_search_execution_successful(self, result: Dict) -> bool:
      # Checks FormattedText for error patterns:
      # - "TooManyRequests"
      # - "Error processing search request"  
      # - "Agentic retrieval failed"
      # - Rate limit exceeded
  ```

- **Product Extraction**:
  ```python
  # Parses AI-generated JSON content
  def _parse_product_content(self, content: str) -> Dict:
      # Extracts: ProductNumber, Price, Name, ItemId, Description
      # Uses regex patterns for field extraction
  ```

- **Throttling Analysis**:
  - Excludes throttled requests from relevance metrics
  - Provides detailed throttling statistics
  - Calculates retry-after timing analysis

- **Enhanced Metrics**:
  - Separate tracking of API success vs search execution success
  - Throttling rate calculation
  - Question-type specific throttling breakdown

## Performance Metrics

Both systems calculate identical relevance metrics:

### Precision/Recall Metrics
- **Precision@K**: Relevant items in top K / K
- **Recall@K**: Relevant items in top K / Total relevant items  
- **F1@K**: Harmonic mean of Precision@K and Recall@K

### Ranking Quality Metrics
- **MAP** (Mean Average Precision): Average of precision values at each relevant result
- **MRR** (Mean Reciprocal Rank): 1/rank of first relevant result
- **NDCG@K**: Normalized Discounted Cumulative Gain

### Coverage Metrics
- Total results returned
- Average results per query
- Zero results rate
- Response time statistics

## Question Type Performance Analysis

Both systems provide detailed breakdowns by question type:

```
EXACT WORD (4 queries):
   P@1: 0.750, P@10: 0.680
   R@1: 0.120, R@10: 0.540
   MAP: 0.720, MRR: 0.750
   Found 15 relevant items, 8 exact matches

CATEGORY (12 queries):
   P@1: 0.917, P@10: 0.842
   R@1: 0.083, R@10: 0.761
   MAP: 0.889, MRR: 0.917
   Found 89 relevant items, 0 exact matches
```

## Error Handling and Reliability

### Dataverse Search
- Standard HTTP error handling
- Direct API response validation
- Simple success/failure classification

### Agentic Search  
- **Multi-layer Error Detection**:
  1. API call success (`success: true`)
  2. Search execution success (no errors in `FormattedText`)
  3. Throttling detection (`TooManyRequests` pattern)
  
- **Throttling Resilience**:
  - Excludes throttled requests from metrics calculation
  - Provides throttling impact analysis
  - Tracks retry-after timing patterns

- **Robustness Features**:
  - Graceful handling of malformed AI responses
  - Fallback scoring for unparseable content
  - Detailed error categorization and reporting

## Usage Recommendations

### Use Dataverse Search When:
- You need consistent, structured data access
- Response time is critical
- You have stable search volume
- Traditional search patterns are sufficient

### Use Agentic Search When:
- You need semantic understanding of complex queries
- Natural language processing is important
- You can handle variable response times
- You need AI-powered result enhancement
- You have proper throttling/retry mechanisms

## Configuration and Customization

Both systems are highly configurable through the `ImprovedRelevanceScorer` class:

### Category Mappings
Add new categories or synonyms by updating `category_mappings` dictionary.

### Attribute Keywords  
Extend `attribute_keywords` for new attribute types.

### Scoring Thresholds
Adjust scoring thresholds in each `_score_*` method for different relevance criteria.

### Question Type Routing
Modify `score_result_relevance()` method to add new question types or change routing logic.

---

*Last Updated: August 17, 2025*
*Generated from: retail-rag-web-app repository*
