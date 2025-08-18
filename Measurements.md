Regarding precision@K and recall@K, I think there is an issue with how the number of relevant items in the top K results is calculated.
We currently have five types of questions:

Exact word – For this question type, I think a result should be considered relevant as long as it contains the exact word.

Category – For this question type, I think a result is relevant as long as it belongs to the same category.

Category + Attribute – For this question type, a result is relevant if it belongs to the same category and its attribute value contains the given attribute value.

Category + Price – For this question type, a result is relevant if it belongs to the same category and its price falls within the price range specified in the question.

Description – For this question type, a result is considered relevant if the description (and the content in each field) is semantically related to the question.