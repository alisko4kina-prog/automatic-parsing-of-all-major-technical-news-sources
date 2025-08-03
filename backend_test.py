import requests
import sys
import json
from datetime import datetime

class TechNewsAPITester:
    def __init__(self, base_url="https://0574c463-e8c8-4430-8a3e-61ac88efae21.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if params:
            print(f"   Params: {params}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return success, response_data
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        if success and isinstance(response, dict):
            print(f"   Message: {response.get('message', 'No message')}")
        return success

    def test_articles_endpoint(self):
        """Test articles endpoint with various parameters"""
        print("\n📰 Testing Articles Endpoint...")
        
        # Test basic articles fetch
        success1, response1 = self.run_test(
            "Get Articles (Basic)",
            "GET",
            "articles",
            200
        )
        
        if success1 and isinstance(response1, dict):
            print(f"   Total articles: {response1.get('total', 0)}")
            print(f"   Articles returned: {len(response1.get('articles', []))}")
            print(f"   Page: {response1.get('page', 'N/A')}")
            print(f"   Per page: {response1.get('per_page', 'N/A')}")
            
            # Check article structure
            articles = response1.get('articles', [])
            if articles:
                article = articles[0]
                required_fields = ['id', 'title', 'summary', 'url', 'source', 'source_name', 'published_date']
                missing_fields = [field for field in required_fields if field not in article]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in article: {missing_fields}")
                else:
                    print(f"   ✅ Article structure looks good")
                    print(f"   Sample article: {article['title'][:50]}...")
        
        # Test pagination
        success2, response2 = self.run_test(
            "Get Articles (Pagination)",
            "GET",
            "articles",
            200,
            params={"page": 2, "per_page": 5}
        )
        
        # Test filtering by hours
        success3, response3 = self.run_test(
            "Get Articles (Last 24 hours)",
            "GET",
            "articles",
            200,
            params={"hours": 24}
        )
        
        # Test search functionality
        success4, response4 = self.run_test(
            "Get Articles (Search)",
            "GET",
            "articles",
            200,
            params={"search": "AI"}
        )
        
        if success4 and isinstance(response4, dict):
            print(f"   Search results for 'AI': {len(response4.get('articles', []))} articles")
        
        return all([success1, success2, success3, success4])

    def test_sources_endpoint(self):
        """Test sources endpoint"""
        success, response = self.run_test(
            "Get Sources",
            "GET",
            "sources",
            200
        )
        
        if success and isinstance(response, dict):
            sources = response.get('sources', [])
            print(f"   Number of sources: {len(sources)}")
            
            expected_sources = ['techcrunch', 'theverge', 'arstechnica', 'wired', 'hackernews']
            found_sources = [s.get('key') for s in sources]
            
            for expected in expected_sources:
                if expected in found_sources:
                    source_data = next(s for s in sources if s.get('key') == expected)
                    print(f"   ✅ {source_data.get('name')}: {source_data.get('article_count', 0)} articles")
                else:
                    print(f"   ❌ Missing source: {expected}")
        
        return success

    def test_stats_endpoint(self):
        """Test statistics endpoint"""
        success, response = self.run_test(
            "Get Statistics",
            "GET",
            "stats",
            200
        )
        
        if success and isinstance(response, dict):
            print(f"   Total articles: {response.get('total_articles', 0)}")
            print(f"   Recent articles (24h): {response.get('recent_articles_24h', 0)}")
            
            by_source = response.get('by_source', [])
            if by_source:
                print(f"   Articles by source:")
                for source_stat in by_source[:3]:  # Show top 3
                    print(f"     - {source_stat.get('_id')}: {source_stat.get('count')} articles")
        
        return success

    def test_refresh_endpoint(self):
        """Test manual refresh endpoint"""
        success, response = self.run_test(
            "Manual Refresh",
            "POST",
            "refresh",
            200
        )
        
        if success and isinstance(response, dict):
            print(f"   Refresh message: {response.get('message', 'No message')}")
        
        return success

    def test_articles_with_source_filter(self):
        """Test articles endpoint with source filtering"""
        print("\n🔍 Testing Source Filtering...")
        
        # Test with specific source
        success, response = self.run_test(
            "Get Articles (TechCrunch only)",
            "GET",
            "articles",
            200,
            params={"source": "techcrunch", "per_page": 10}
        )
        
        if success and isinstance(response, dict):
            articles = response.get('articles', [])
            if articles:
                # Verify all articles are from TechCrunch
                techcrunch_articles = [a for a in articles if a.get('source') == 'techcrunch']
                print(f"   TechCrunch articles: {len(techcrunch_articles)}/{len(articles)}")
                if len(techcrunch_articles) == len(articles):
                    print(f"   ✅ Source filtering working correctly")
                else:
                    print(f"   ❌ Source filtering not working properly")
        
        return success

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n⚠️  Testing Edge Cases...")
        
        # Test invalid page number
        success1, _ = self.run_test(
            "Invalid Page Number",
            "GET",
            "articles",
            422,  # Validation error expected
            params={"page": 0}
        )
        
        # Test invalid per_page
        success2, _ = self.run_test(
            "Invalid Per Page",
            "GET",
            "articles",
            422,  # Validation error expected
            params={"per_page": 200}  # Over limit
        )
        
        # Test invalid hours
        success3, _ = self.run_test(
            "Invalid Hours Filter",
            "GET",
            "articles",
            422,  # Validation error expected
            params={"hours": 200}  # Over limit
        )
        
        # Test empty search
        success4, response4 = self.run_test(
            "Empty Search Results",
            "GET",
            "articles",
            200,
            params={"search": "xyznonexistentterm123"}
        )
        
        if success4 and isinstance(response4, dict):
            articles = response4.get('articles', [])
            print(f"   Empty search returned: {len(articles)} articles")
        
        return True  # Edge cases are expected to fail in some cases

def main():
    print("🚀 Starting Tech News Aggregator API Tests")
    print("=" * 60)
    
    tester = TechNewsAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_sources_endpoint,
        tester.test_stats_endpoint,
        tester.test_articles_endpoint,
        tester.test_articles_with_source_filter,
        tester.test_refresh_endpoint,
        tester.test_edge_cases
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())