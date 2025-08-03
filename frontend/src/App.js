import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Search, RefreshCw, Clock, ExternalLink, Tag, TrendingUp, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedHours, setSelectedHours] = useState('24');
  const [sources, setSources] = useState([]);
  const [stats, setStats] = useState(null);
  const [page, setPage] = useState(1);
  const [totalArticles, setTotalArticles] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Fetch sources
  const fetchSources = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/sources`);
      setSources(response.data.sources);
    } catch (error) {
      console.error('Error fetching sources:', error);
    }
  }, []);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  // Fetch articles
  const fetchArticles = useCallback(async (isNewSearch = false) => {
    try {
      if (isNewSearch) {
        setLoading(true);
        setPage(1);
      }

      const params = {
        page: isNewSearch ? 1 : page,
        per_page: 20,
        hours: selectedHours === 'all' ? undefined : parseInt(selectedHours),
        source: selectedSource === 'all' ? undefined : selectedSource,
        search: searchTerm || undefined
      };

      // Remove undefined parameters
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);

      const response = await axios.get(`${API}/articles`, { params });
      
      if (isNewSearch) {
        setArticles(response.data.articles);
      } else {
        setArticles(prev => [...prev, ...response.data.articles]);
      }
      
      setTotalArticles(response.data.total);
      setHasMore(response.data.articles.length === 20);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching articles:', error);
      setLoading(false);
    }
  }, [page, searchTerm, selectedSource, selectedHours]);

  // Manual refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/refresh`);
      await fetchArticles(true);
      await fetchStats();
    } catch (error) {
      console.error('Error refreshing:', error);
    }
    setRefreshing(false);
  };

  // Load more articles
  const loadMore = () => {
    if (hasMore && !loading) {
      setPage(prev => prev + 1);
    }
  };

  // Search handler
  const handleSearch = (e) => {
    e.preventDefault();
    fetchArticles(true);
  };

  // Format date
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return `${Math.floor(diffInHours * 60)} minutes ago`;
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)} hours ago`;
    } else {
      return `${Math.floor(diffInHours / 24)} days ago`;
    }
  };

  // Initial load
  useEffect(() => {
    fetchSources();
    fetchStats();
    fetchArticles(true);
  }, [fetchSources, fetchStats]);

  // Fetch articles when filters change
  useEffect(() => {
    if (!loading) {
      fetchArticles(true);
    }
  }, [selectedSource, selectedHours]);

  // Load more when page changes
  useEffect(() => {
    if (page > 1) {
      fetchArticles();
    }
  }, [page, fetchArticles]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats();
      if (page === 1) {
        fetchArticles(true);
      }
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [page]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-md border-b border-white/10 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">TechNewsHub</h1>
                  <p className="text-xs text-gray-400">Live Tech News Aggregator</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {stats && (
                <div className="hidden sm:flex items-center space-x-6 text-sm">
                  <div className="text-center">
                    <div className="text-white font-semibold">{stats.total_articles?.toLocaleString()}</div>
                    <div className="text-gray-400">Total Articles</div>
                  </div>
                  <div className="text-center">
                    <div className="text-green-400 font-semibold">{stats.recent_articles_24h}</div>
                    <div className="text-gray-400">Last 24h</div>
                  </div>
                </div>
              )}
              
              <Button
                onClick={handleRefresh}
                disabled={refreshing}
                variant="outline"
                size="sm"
                className="border-white/20 hover:bg-white/10"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                <span className="ml-2 hidden sm:inline">Refresh</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="mb-8">
          <Card className="bg-white/5 backdrop-blur-sm border-white/10">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Search */}
                <form onSubmit={handleSearch} className="md:col-span-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      type="text"
                      placeholder="Search articles..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10 bg-white/10 border-white/20 text-white placeholder-gray-400"
                    />
                  </div>
                </form>

                {/* Source Filter */}
                <Select value={selectedSource} onValueChange={setSelectedSource}>
                  <SelectTrigger className="bg-white/10 border-white/20 text-white">
                    <Filter className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="All Sources" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-white/20">
                    <SelectItem value="all">All Sources</SelectItem>
                    {sources.map((source) => (
                      <SelectItem key={source.key} value={source.key}>
                        <div className="flex items-center space-x-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: source.color }}
                          />
                          <span>{source.name}</span>
                          <Badge variant="secondary" className="ml-auto text-xs">
                            {source.article_count}
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Time Filter */}
                <Select value={selectedHours} onValueChange={setSelectedHours}>
                  <SelectTrigger className="bg-white/10 border-white/20 text-white">
                    <Clock className="h-4 w-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-white/20">
                    <SelectItem value="1">Last Hour</SelectItem>
                    <SelectItem value="6">Last 6 Hours</SelectItem>
                    <SelectItem value="24">Last 24 Hours</SelectItem>
                    <SelectItem value="72">Last 3 Days</SelectItem>
                    <SelectItem value="168">Last Week</SelectItem>
                    <SelectItem value="all">All Time</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Articles Grid */}
        {loading && page === 1 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="bg-white/5 backdrop-blur-sm border-white/10 animate-pulse">
                <CardContent className="p-6">
                  <div className="h-4 bg-white/10 rounded mb-3"></div>
                  <div className="h-3 bg-white/10 rounded mb-2"></div>
                  <div className="h-3 bg-white/10 rounded mb-4"></div>
                  <div className="flex items-center justify-between">
                    <div className="h-3 bg-white/10 rounded w-20"></div>
                    <div className="h-3 bg-white/10 rounded w-16"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((article, index) => (
                <Card 
                  key={`${article.id}-${index}`} 
                  className="bg-white/5 backdrop-blur-sm border-white/10 hover:bg-white/10 transition-all duration-300 group hover:scale-[1.02] hover:shadow-2xl"
                >
                  {article.image_url && (
                    <div className="relative overflow-hidden rounded-t-lg">
                      <img
                        src={article.image_url}
                        alt={article.title}
                        className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      <div className="absolute top-3 left-3">
                        <Badge 
                          className="text-white text-xs font-medium"
                          style={{ backgroundColor: article.source_color }}
                        >
                          {article.source_name}
                        </Badge>
                      </div>
                    </div>
                  )}
                  
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-3">
                      {!article.image_url && (
                        <Badge 
                          className="text-white text-xs font-medium"
                          style={{ backgroundColor: article.source_color }}
                        >
                          {article.source_name}
                        </Badge>
                      )}
                      <div className="text-xs text-gray-400 flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {formatDate(article.published_date)}
                      </div>
                    </div>
                    
                    <CardTitle className="text-white text-lg font-bold mb-3 line-clamp-2 group-hover:text-blue-300 transition-colors">
                      {article.title}
                    </CardTitle>
                    
                    <p className="text-gray-300 text-sm line-clamp-3 mb-4">
                      {article.summary}
                    </p>
                    
                    {article.tags && article.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-4">
                        {article.tags.slice(0, 3).map((tag, tagIndex) => (
                          <Badge key={tagIndex} variant="secondary" className="text-xs bg-white/10 text-gray-300 hover:bg-white/20">
                            <Tag className="h-2 w-2 mr-1" />
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors"
                    >
                      Read More
                      <ExternalLink className="h-3 w-3 ml-1" />
                    </a>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Load More Button */}
            {hasMore && !loading && articles.length > 0 && (
              <div className="mt-12 text-center">
                <Button
                  onClick={loadMore}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3"
                >
                  Load More Articles
                </Button>
              </div>
            )}

            {/* No Results */}
            {!loading && articles.length === 0 && (
              <div className="text-center py-12">
                <div className="text-gray-400 text-lg mb-4">No articles found</div>
                <p className="text-gray-500">Try adjusting your search terms or filters</p>
              </div>
            )}
          </>
        )}

        {/* Loading More */}
        {loading && page > 1 && (
          <div className="text-center py-8">
            <div className="inline-flex items-center text-gray-400">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" />
              Loading more articles...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;