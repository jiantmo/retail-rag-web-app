// Enhanced Search Results Display
class SearchResultsRenderer {
    constructor() {
        this.initializeEventHandlers();
    }

    initializeEventHandlers() {
        // Add any global event handlers here
    }

    renderFormattedResponse(response, containerElement) {
        if (!response || !containerElement) {
            console.error('Invalid response or container element');
            return;
        }

        try {
            if (response.success || response.Success) {
                this.renderSuccessResponse(response, containerElement);
            } else {
                this.renderErrorResponse(response, containerElement);
            }
        } catch (error) {
            console.error('Error rendering formatted response:', error);
            this.renderFallbackError(containerElement, error.message);
        }
    }

    renderSuccessResponse(response, containerElement) {
        const searchTypeIcon = this.getSearchTypeIcon(response.searchType);
        const searchTypeColor = this.getSearchTypeColor(response.searchType);

        const html = `
            <div class="search-results animated fadeIn">
                <!-- Header Section -->
                <div class="results-header bg-gradient-${searchTypeColor} text-white p-4 rounded-top shadow-sm">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <i class="fas ${searchTypeIcon} fa-2x me-3"></i>
                            <div>
                                <h4 class="mb-1">${response.searchType} Results</h4>
                                <p class="mb-0 opacity-75">
                                    <i class="fas fa-quote-left me-2"></i>
                                    "${response.query}"
                                </p>
                            </div>
                        </div>
                        <div class="text-end">
                            <div class="badge bg-light text-dark px-3 py-2">
                                <i class="fas fa-clock me-1"></i>
                                ${response.metadata?.processingTimeMs || 0}ms
                            </div>
                            ${response.metadata?.totalResults ? `
                                <div class="badge bg-light text-dark px-3 py-2 mt-1">
                                    <i class="fas fa-search me-1"></i>
                                    ${response.metadata.totalResults} results
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>

                <!-- Content Section -->
                <div class="results-content bg-white shadow-sm">
                    ${this.renderMainContent(response)}
                    ${this.renderMetadataSection(response)}
                </div>
            </div>
        `;

        containerElement.innerHTML = html;
        this.initializeInteractiveElements(containerElement);
    }

    renderMainContent(response) {
        let contentHtml = '';

        // Debug logging
        console.log('Rendering response:', response);

        // Get result with case-insensitive access
        const result = response.result || response.Result || {};
        const summary = result.summary || result.Summary;
        const products = result.products || result.Products || [];
        const recommendations = result.recommendations || result.Recommendations || [];
        const insights = result.insights || result.Insights || [];
        const explanation = result.explanation || result.Explanation;

        console.log('Extracted data:', { summary, productsCount: products.length, result });

        // Summary Section
        if (summary) {
            contentHtml += `
                <div class="summary-section p-4 border-bottom">
                    <div class="d-flex align-items-start">
                        <div class="summary-icon bg-primary bg-opacity-10 rounded-circle p-2 me-3 mt-1">
                            <i class="fas fa-lightbulb text-primary"></i>
                        </div>
                        <div class="flex-grow-1">
                            <h5 class="text-primary mb-2">
                                <i class="fas fa-robot me-2"></i>AI Summary
                            </h5>
                            <div class="summary-content">
                                ${this.formatTextContent(summary)}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Products Section
        if (products && products.length > 0) {
            contentHtml += this.renderProductsSection(products);
        }

        // Recommendations Section
        if (recommendations && recommendations.length > 0) {
            contentHtml += this.renderRecommendationsSection(recommendations);
        }

        // Insights Section
        if (insights && insights.length > 0) {
            contentHtml += this.renderInsightsSection(insights);
        }

        // Explanation Section
        if (explanation) {
            contentHtml += `
                <div class="explanation-section p-4 bg-light border-top">
                    <div class="d-flex align-items-start">
                        <i class="fas fa-info-circle text-info me-2 mt-1"></i>
                        <div>
                            <h6 class="text-info mb-2">How this search worked</h6>
                            <p class="mb-0 text-muted small">${explanation}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        return contentHtml;
    }

    renderProductsSection(products) {
        const productsHtml = products.map(product => this.renderProductCard(product)).join('');
        
        return `
            <div class="products-section p-4 border-bottom">
                <h5 class="mb-3">
                    <i class="fas fa-shopping-bag text-success me-2"></i>
                    Recommended Products (${products.length})
                </h5>
                <div class="products-grid">
                    ${productsHtml}
                </div>
            </div>
        `;
    }

    renderProductCard(product) {
        const priceDisplay = product.price > 0 ? `$${product.price.toFixed(2)}` : 'Price not available';
        const relevancePercentage = Math.round(product.relevanceScore * 100);
        
        return `
            <div class="product-card mb-3 p-3 border rounded-3 hover-lift transition-all">
                <div class="row g-3">
                    <div class="col-md-3 col-lg-2">
                        <div class="product-image-container">
                            ${product.imageUrls && product.imageUrls.length > 0 ? `
                                <img src="${product.imageUrls[0]}" alt="${product.name}" class="product-image">
                            ` : `
                                <div class="product-placeholder">
                                    <i class="fas fa-image fa-2x"></i>
                                    <small>No Image</small>
                                </div>
                            `}
                        </div>
                    </div>
                    <div class="col-md-9 col-lg-10">
                        <div class="product-details h-100 d-flex flex-column">
                            <div class="product-header mb-2">
                                <h6 class="product-title mb-1">${product.name}</h6>
                                <div class="d-flex align-items-center gap-2 mb-2">
                                    <span class="product-price badge bg-success fs-6">${priceDisplay}</span>
                                    ${product.productNumber ? `
                                        <span class="product-number text-muted small">SKU: ${product.productNumber}</span>
                                    ` : ''}
                                    <span class="relevance-badge badge bg-info">
                                        ${relevancePercentage}% match
                                    </span>
                                </div>
                            </div>
                            
                            ${product.description ? `
                                <p class="product-description text-muted small mb-2">${product.description}</p>
                            ` : ''}
                            
                            <div class="product-attributes">
                                ${product.color ? `
                                    <span class="attribute-badge color-badge">
                                        <i class="fas fa-palette me-1"></i>${product.color}
                                    </span>
                                ` : ''}
                                ${product.size ? `
                                    <span class="attribute-badge size-badge">
                                        <i class="fas fa-expand-arrows-alt me-1"></i>${product.size}
                                    </span>
                                ` : ''}
                                ${product.material ? `
                                    <span class="attribute-badge material-badge">
                                        <i class="fas fa-cube me-1"></i>${product.material}
                                    </span>
                                ` : ''}
                            </div>
                            
                            ${product.whyRecommended ? `
                                <div class="recommendation-reason mt-2 p-2 bg-light rounded-2">
                                    <small class="text-primary">
                                        <i class="fas fa-thumbs-up me-1"></i>
                                        <strong>Why recommended:</strong> ${product.whyRecommended}
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderRecommendationsSection(recommendations) {
        const recommendationsHtml = recommendations.map(rec => `
            <div class="recommendation-item p-3 border rounded-3 mb-2 hover-lift transition-all">
                <div class="d-flex align-items-start">
                    <div class="recommendation-icon bg-warning bg-opacity-10 rounded-circle p-2 me-3">
                        <i class="fas ${rec.icon} text-warning"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${rec.title}</h6>
                        <p class="mb-2 text-muted small">${rec.description}</p>
                        ${rec.tags && rec.tags.length > 0 ? `
                            <div class="recommendation-tags">
                                ${rec.tags.map(tag => `
                                    <span class="badge bg-light text-dark me-1">${tag}</span>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="recommendations-section p-4 border-bottom">
                <h5 class="mb-3">
                    <i class="fas fa-magic text-warning me-2"></i>
                    AI Recommendations
                </h5>
                ${recommendationsHtml}
            </div>
        `;
    }

    renderInsightsSection(insights) {
        const insightsHtml = insights.map(insight => {
            const colorClass = this.getInsightColorClass(insight.color);
            return `
                <div class="insight-item alert alert-${colorClass} border-0 rounded-3 mb-2">
                    <div class="d-flex align-items-start">
                        <i class="fas ${insight.icon} me-2 mt-1"></i>
                        <div>
                            <h6 class="alert-heading mb-1">${insight.title}</h6>
                            <p class="mb-0 small">${insight.content}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="insights-section p-4 border-bottom">
                <h5 class="mb-3">
                    <i class="fas fa-chart-line text-info me-2"></i>
                    Insights & Tips
                </h5>
                ${insightsHtml}
            </div>
        `;
    }

    renderMetadataSection(response) {
        if (!response.metadata) return '';

        let metadataHtml = '';

        // Sub-queries for Agentic search
        if (response.metadata.subQueries && response.metadata.subQueries.length > 0) {
            metadataHtml += this.renderSubQueriesSection(response.metadata.subQueries);
        }

        // Token usage
        if (response.metadata.tokenUsage && response.metadata.tokenUsage.totalTokens > 0) {
            metadataHtml += this.renderTokenUsageSection(response.metadata.tokenUsage);
        }

        // Sources
        if (response.metadata.sources && response.metadata.sources.length > 0) {
            metadataHtml += this.renderSourcesSection(response.metadata.sources);
        }

        // Search stats
        if (response.metadata.stats) {
            metadataHtml += this.renderStatsSection(response.metadata.stats, response.metadata);
        }

        return metadataHtml;
    }

    renderSubQueriesSection(subQueries) {
        return `
            <div class="sub-queries-section p-4 border-bottom bg-light">
                <div class="d-flex align-items-center justify-content-between mb-3">
                    <h6 class="mb-0">
                        <i class="fas fa-sitemap text-primary me-2"></i>
                        Query Breakdown
                    </h6>
                    <button class="btn btn-sm btn-outline-primary" onclick="toggleSubQueries()">
                        <i class="fas fa-chevron-down me-1" id="subQueriesIcon"></i>
                        <span id="subQueriesText">Show Details</span>
                    </button>
                </div>
                
                <p class="text-muted small mb-3">
                    AI decomposed your query into ${subQueries.length} optimized sub-queries for parallel execution
                </p>
                
                <div id="subQueriesDetails" style="display: none;">
                    <div class="row g-3">
                        ${subQueries.map((subQuery, index) => `
                            <div class="col-md-6 col-lg-4">
                                <div class="sub-query-card p-3 bg-white rounded-3 border hover-lift">
                                    <div class="d-flex align-items-start">
                                        <div class="sub-query-number bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 28px; height: 28px; font-size: 0.8rem; font-weight: bold;">
                                            ${index + 1}
                                        </div>
                                        <div class="flex-grow-1">
                                            <div class="sub-query-text mb-2">
                                                <strong>"${subQuery.query}"</strong>
                                            </div>
                                            <div class="sub-query-meta">
                                                <small class="text-muted">
                                                    <i class="fas fa-search me-1"></i>
                                                    ${subQuery.resultCount} results
                                                    ${subQuery.elapsedMs > 0 ? `
                                                        <span class="ms-2">
                                                            <i class="fas fa-clock me-1"></i>${subQuery.elapsedMs}ms
                                                        </span>
                                                    ` : ''}
                                                </small>
                                            </div>
                                            ${subQuery.purpose ? `
                                                <div class="sub-query-purpose mt-1">
                                                    <small class="text-primary">
                                                        <i class="fas fa-lightbulb me-1"></i>${subQuery.purpose}
                                                    </small>
                                                </div>
                                            ` : ''}
                                        </div>
                                    </div>
                                    ${subQuery.filter ? `
                                        <div class="sub-query-filter mt-2 p-2 bg-light rounded-2">
                                            <small class="text-muted">
                                                <i class="fas fa-filter me-1"></i>
                                                Filter: ${subQuery.filter}
                                            </small>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    renderTokenUsageSection(tokenUsage) {
        return `
            <div class="token-usage-section p-4 border-bottom">
                <h6 class="mb-3">
                    <i class="fas fa-coins text-warning me-2"></i>
                    Token Usage & Cost
                </h6>
                <div class="row g-3">
                    <div class="col-md-3">
                        <div class="stat-card text-center p-3 bg-light rounded-3">
                            <div class="stat-value h5 mb-1 text-primary">${tokenUsage.inputTokens.toLocaleString()}</div>
                            <div class="stat-label small text-muted">Input Tokens</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center p-3 bg-light rounded-3">
                            <div class="stat-value h5 mb-1 text-success">${tokenUsage.outputTokens.toLocaleString()}</div>
                            <div class="stat-label small text-muted">Output Tokens</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center p-3 bg-light rounded-3">
                            <div class="stat-value h5 mb-1 text-info">${tokenUsage.totalTokens.toLocaleString()}</div>
                            <div class="stat-label small text-muted">Total Tokens</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card text-center p-3 bg-light rounded-3">
                            <div class="stat-value h5 mb-1 text-warning">$${tokenUsage.estimatedCost.toFixed(4)}</div>
                            <div class="stat-label small text-muted">Est. Cost</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderSourcesSection(sources) {
        const sourcesHtml = sources.slice(0, 6).map((source, index) => `
            <div class="col-md-6 col-lg-4">
                <div class="source-item p-2 bg-white rounded-2 border hover-lift h-100">
                    <div class="d-flex align-items-start">
                        <div class="source-number bg-secondary text-white rounded-circle d-flex align-items-center justify-content-center me-2 flex-shrink-0" style="width: 24px; height: 24px; font-size: 0.7rem;">
                            ${index + 1}
                        </div>
                        <div class="flex-grow-1 min-width-0">
                            <div class="source-title text-truncate small fw-semibold" title="${source.title}">
                                ${source.title || 'Document ' + (index + 1)}
                            </div>
                            <div class="source-type text-muted" style="font-size: 0.7rem;">
                                <i class="fas fa-file-alt me-1"></i>${source.type}
                            </div>
                            ${source.relevanceScore ? `
                                <div class="source-relevance mt-1">
                                    <span class="badge bg-light text-dark" style="font-size: 0.6rem;">
                                        ${Math.round(source.relevanceScore * 100)}% relevance
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="sources-section p-4 border-bottom bg-light">
                <h6 class="mb-3">
                    <i class="fas fa-link text-secondary me-2"></i>
                    Source Documents (${sources.length})
                </h6>
                <div class="row g-2">
                    ${sourcesHtml}
                </div>
                ${sources.length > 6 ? `
                    <div class="mt-3 text-center">
                        <small class="text-muted">
                            Showing 6 of ${sources.length} sources
                            <button class="btn btn-link btn-sm p-0 ms-1" onclick="toggleAllSources()">
                                Show all
                            </button>
                        </small>
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderStatsSection(stats, metadata) {
        return `
            <div class="stats-section p-4 bg-light">
                <h6 class="mb-3">
                    <i class="fas fa-chart-bar text-info me-2"></i>
                    Search Statistics
                </h6>
                <div class="row g-3">
                    ${stats.planningOperations > 0 ? `
                        <div class="col-6 col-md-3">
                            <div class="stat-item text-center">
                                <div class="stat-value h6 mb-1 text-primary">${stats.planningOperations}</div>
                                <div class="stat-label small text-muted">Planning Operations</div>
                            </div>
                        </div>
                    ` : ''}
                    ${stats.parallelQueries > 0 ? `
                        <div class="col-6 col-md-3">
                            <div class="stat-item text-center">
                                <div class="stat-value h6 mb-1 text-success">${stats.parallelQueries}</div>
                                <div class="stat-label small text-muted">Parallel Queries</div>
                            </div>
                        </div>
                    ` : ''}
                    ${stats.documentsSearched > 0 ? `
                        <div class="col-6 col-md-3">
                            <div class="stat-item text-center">
                                <div class="stat-value h6 mb-1 text-info">${stats.documentsSearched}</div>
                                <div class="stat-label small text-muted">Documents Searched</div>
                            </div>
                        </div>
                    ` : ''}
                    <div class="col-6 col-md-3">
                        <div class="stat-item text-center">
                            <div class="stat-value h6 mb-1 text-warning">${metadata.processingTimeMs || 0}ms</div>
                            <div class="stat-label small text-muted">Processing Time</div>
                        </div>
                    </div>
                </div>
                ${metadata.searchStrategy ? `
                    <div class="mt-3">
                        <small class="text-muted">
                            <i class="fas fa-cog me-1"></i>
                            Strategy: ${metadata.searchStrategy}
                        </small>
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderErrorResponse(response, containerElement) {
        const searchTypeIcon = this.getSearchTypeIcon(response.searchType);
        
        const html = `
            <div class="search-results">
                <div class="alert alert-danger border-0 rounded-4 shadow-sm">
                    <div class="d-flex align-items-center">
                        <div class="alert-icon me-3">
                            <i class="fas fa-exclamation-triangle fa-2x"></i>
                        </div>
                        <div class="flex-grow-1">
                            <h5 class="alert-heading">
                                <i class="fas ${searchTypeIcon} me-2"></i>
                                ${response.searchType} Error
                            </h5>
                            <p class="mb-2">${response.error || 'An unexpected error occurred.'}</p>
                            ${response.query ? `
                                <small class="text-muted">
                                    <strong>Query:</strong> "${response.query}"
                                </small>
                            ` : ''}
                            ${response.metadata?.processingTimeMs ? `
                                <div class="mt-2">
                                    <small class="text-muted">
                                        <i class="fas fa-clock me-1"></i>
                                        Processing time: ${response.metadata.processingTimeMs}ms
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;

        containerElement.innerHTML = html;
    }

    renderFallbackError(containerElement, errorMessage) {
        const html = `
            <div class="search-results">
                <div class="alert alert-warning border-0 rounded-4">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-exclamation-circle fa-2x me-3"></i>
                        <div>
                            <h5 class="alert-heading">Display Error</h5>
                            <p class="mb-0">Unable to properly display search results: ${errorMessage}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        containerElement.innerHTML = html;
    }

    initializeInteractiveElements(containerElement) {
        // Add hover effects and animations
        const cards = containerElement.querySelectorAll('.hover-lift');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
        });

        // Add click handlers for expandable sections
        this.initializeExpandableSections(containerElement);
    }

    initializeExpandableSections(containerElement) {
        // Sub-queries toggle is handled by global function
        // Add other expandable section handlers here if needed
    }

    formatTextContent(text) {
        if (!text) return '';
        
        // Convert newlines to HTML breaks
        text = text.replace(/\n/g, '<br>');
        
        // Make **bold** text bold
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Make *italic* text italic
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return text;
    }

    getSearchTypeIcon(searchType) {
        switch (searchType?.toLowerCase()) {
            case 'rag search':
                return 'fa-robot';
            case 'agentic ai search':
            case 'agentic search':
                return 'fa-brain';
            case 'dataverse search':
                return 'fa-database';
            default:
                return 'fa-search';
        }
    }

    getSearchTypeColor(searchType) {
        switch (searchType?.toLowerCase()) {
            case 'rag search':
                return 'primary';
            case 'agentic ai search':
            case 'agentic search':
                return 'info';
            case 'dataverse search':
                return 'secondary';
            default:
                return 'primary';
        }
    }

    getInsightColorClass(color) {
        const colorMap = {
            'info': 'info',
            'warning': 'warning',
            'success': 'success',
            'danger': 'danger',
            'primary': 'primary',
            'secondary': 'secondary'
        };
        return colorMap[color] || 'info';
    }
}

// Global functions for UI interactions
function toggleSubQueries() {
    const details = document.getElementById('subQueriesDetails');
    const icon = document.getElementById('subQueriesIcon');
    const text = document.getElementById('subQueriesText');
    
    if (details && icon && text) {
        if (details.style.display === 'none') {
            details.style.display = 'block';
            icon.className = 'fas fa-chevron-up me-1';
            text.textContent = 'Hide Details';
            
            // Smooth animation
            details.style.opacity = '0';
            details.style.transform = 'translateY(-10px)';
            details.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            
            setTimeout(() => {
                details.style.opacity = '1';
                details.style.transform = 'translateY(0)';
            }, 10);
        } else {
            details.style.opacity = '0';
            details.style.transform = 'translateY(-10px)';
            
            setTimeout(() => {
                details.style.display = 'none';
                icon.className = 'fas fa-chevron-down me-1';
                text.textContent = 'Show Details';
            }, 300);
        }
    }
}

function toggleAllSources() {
    // Implementation for showing all sources
    console.log('Toggle all sources');
}

// Initialize the renderer
const searchResultsRenderer = new SearchResultsRenderer();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchResultsRenderer;
}
