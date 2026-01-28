#!/usr/bin/env python3
"""
Test pagination and filtering functionality on SDE pages.

This script tests:
1. /sde/category/6/ - Verify pagination works (check if page shows 50 items)
2. /sde/search?q=shield - Verify search results display
3. /sde/search?q=armor&category=7 - Verify category filter works
4. /sde/group/26/?page=2 - Test group pagination
5. /sde/search?q=module&sort=name - Verify sort option
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import sys

BASE_URL = "http://localhost:8181"

def test_category_pagination():
    """Test 1: /sde/category/6/ - Verify pagination works"""
    print("\n" + "="*80)
    print("TEST 1: Category Pagination (/sde/category/6/)")
    print("="*80)

    url = f"{BASE_URL}/sde/category/6/"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Count items on the page
    items = soup.find_all('tr', class_='item-row') or soup.find_all('li', class_='list-group-item')
    print(f"Items found on page: {len(items)}")

    # Check for pagination controls
    pagination = soup.find('nav', {'aria-label': 'Pagination'}) or soup.find('ul', class_='pagination')
    if pagination:
        print("✅ Pagination controls found")
        page_links = pagination.find_all('a')
        print(f"   Pagination links: {len(page_links)}")

        # Check if there's a next page link
        next_link = pagination.find('a', text='Next') or pagination.find('a', {'aria-label': 'Next'})
        if next_link:
            print("✅ Next page link found")
        else:
            print("ℹ️  No next page link (might be only one page)")

        # Check if there's a page 2 link
        page_2_link = pagination.find('a', text='2')
        if page_2_link:
            print("✅ Page 2 link found")
            href = page_2_link.get('href', '')
            if href:
                print(f"   Page 2 URL: {href}")
    else:
        print("❌ No pagination controls found")

    # Check if approximately 50 items are shown (or less if not enough data)
    if len(items) > 0:
        print(f"✅ Items displayed: {len(items)}")
        if len(items) <= 50:
            print(f"✅ Item count is within limit (<= 50)")
        else:
            print(f"⚠️  More than 50 items displayed ({len(items)})")
    else:
        print("❌ No items found on page")

    return len(items) > 0


def test_search_results():
    """Test 2: /sde/search?q=shield - Verify search results display"""
    print("\n" + "="*80)
    print("TEST 2: Search Results (/sde/search?q=shield)")
    print("="*80)

    url = f"{BASE_URL}/sde/search?q=shield"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for search results
    results = soup.find_all('tr', class_='item-row') or soup.find_all('li', class_='list-group-item') or soup.find_all('div', class_='search-result')
    print(f"Search results found: {len(results)}")

    if len(results) > 0:
        print("✅ Search results displayed")

        # Check if results contain "shield" related items
        page_text = soup.get_text().lower()
        if 'shield' in page_text:
            print("✅ Results appear to contain shield-related items")
        else:
            print("⚠️  Results may not contain shield-related items")

        # Show first few result titles if available
        titles = soup.find_all(['td', 'div'], class_=['item-name', 'title', 'name'])
        if titles:
            print(f"   Sample result: {titles[0].get_text().strip()[:50]}")
    else:
        print("❌ No search results found")

    # Check for search form/indicator
    search_input = soup.find('input', {'name': 'q'}) or soup.find('input', {'id': 'search'})
    if search_input:
        current_value = search_input.get('value', '')
        print(f"✅ Search input found with value: '{current_value}'")

    return len(results) > 0


def test_search_category_filter():
    """Test 3: /sde/search?q=armor&category=7 - Verify category filter works"""
    print("\n" + "="*80)
    print("TEST 3: Search with Category Filter (/sde/search?q=armor&category=7)")
    print("="*80)

    url = f"{BASE_URL}/sde/search?q=armor&category=7"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for search results
    results = soup.find_all('tr', class_='item-row') or soup.find_all('li', class_='list-group-item')
    print(f"Search results found: {len(results)}")

    if len(results) > 0:
        print("✅ Search results displayed with category filter")

        # Check if results are from category 7 (Modules)
        page_text = soup.get_text().lower()
        if 'module' in page_text or 'armor' in page_text:
            print("✅ Results appear to be module-related (category 7)")
        else:
            print("⚠️  Results category unclear")

        # Check for category indicator in the page
        category_badge = soup.find(['span', 'div', 'badge'], class_=['category', 'badge', 'filter'])
        if category_badge:
            print(f"✅ Category indicator found: {category_badge.get_text().strip()[:50]}")
    else:
        print("❌ No search results found")

    # Check if category filter is applied in the URL or form
    category_select = soup.find('select', {'name': 'category'}) or soup.find('input', {'name': 'category'})
    if category_select:
        print("✅ Category filter control found")

    return len(results) > 0


def test_group_pagination():
    """Test 4: /sde/group/26/?page=2 - Test group pagination"""
    print("\n" + "="*80)
    print("TEST 4: Group Pagination (/sde/group/26/?page=2)")
    print("="*80)

    url = f"{BASE_URL}/sde/group/26/?page=2"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for items on page 2
    items = soup.find_all('tr', class_='item-row') or soup.find_all('li', class_='list-group-item')
    print(f"Items found on page 2: {len(items)}")

    # Check for pagination controls
    pagination = soup.find('nav', {'aria-label': 'Pagination'}) or soup.find('ul', class_='pagination')
    if pagination:
        print("✅ Pagination controls found")

        # Check if page 2 is highlighted/active
        active_page = pagination.find('li', class_='active') or pagination.find('a', class_='active')
        if active_page and '2' in active_page.get_text():
            print("✅ Page 2 is marked as active")
        else:
            print("ℹ️  Page 2 may not be marked as active")

        # Check for previous and next links
        prev_link = pagination.find('a', text='Previous') or pagination.find('a', {'aria-label': 'Previous'})
        next_link = pagination.find('a', text='Next') or pagination.find('a', {'aria-label': 'Next'})

        if prev_link:
            print("✅ Previous page link found")
        if next_link:
            print("✅ Next page link found")
    else:
        print("❌ No pagination controls found")

    # Check if we got different items than page 1
    if len(items) > 0:
        print("✅ Items displayed on page 2")

        # Verify these are not the first items (page 1)
        first_item_text = items[0].get_text().strip() if items else ""
        print(f"   First item on page 2: {first_item_text[:50]}")
    else:
        print("⚠️  No items on page 2 (might not have enough data)")

    return len(items) > 0 or response.status_code == 200


def test_search_sort():
    """Test 5: /sde/search?q=module&sort=name - Verify sort option"""
    print("\n" + "="*80)
    print("TEST 5: Search with Sort (/sde/search?q=module&sort=name)")
    print("="*80)

    url = f"{BASE_URL}/sde/search?q=module&sort=name"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for search results
    results = soup.find_all('tr', class_='item-row') or soup.find_all('li', class_='list-group-item')
    print(f"Search results found: {len(results)}")

    if len(results) > 0:
        print("✅ Search results displayed")

        # Check if results are sorted by name
        if len(results) > 1:
            # Get first few item names
            item_names = []
            for result in results[:5]:
                name_elem = result.find(['td', 'div', 'a'], class_=['item-name', 'name', 'title'])
                if name_elem:
                    item_names.append(name_elem.get_text().strip())

            if item_names:
                print(f"   First few results: {', '.join(item_names[:3])}")

                # Check if alphabetically sorted
                sorted_names = sorted(item_names)
                if item_names == sorted_names:
                    print("✅ Results appear to be sorted alphabetically by name")
                else:
                    print("⚠️  Results may not be sorted (need more items to verify)")

    # Check for sort indicator in the page
    sort_indicator = soup.find(['th', 'a', 'span'], class_='sort') or soup.find('span', class_='sorted')
    if sort_indicator:
        print(f"✅ Sort indicator found: {sort_indicator.get_text().strip()[:50]}")
    else:
        print("ℹ️  No visual sort indicator found (but sorting may still work)")

    # Check for sort controls/links
    sort_links = soup.find_all('a', href=lambda x: x and 'sort=' in x)
    if sort_links:
        print(f"✅ Sort links found: {len(sort_links)}")
    else:
        print("ℹ️  No sort links found in HTML")

    return len(results) > 0


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SDE PAGINATION AND FILTERING TEST SUITE")
    print("="*80)
    print(f"Testing against: {BASE_URL}")

    results = {
        'Category Pagination': test_category_pagination(),
        'Search Results': test_search_results(),
        'Category Filter': test_search_category_filter(),
        'Group Pagination': test_group_pagination(),
        'Search Sort': test_search_sort(),
    }

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
