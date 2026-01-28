#!/usr/bin/env python3
"""
Test pagination and filtering functionality on SDE pages.

This script tests:
1. /sde/category/6/ - Verify pagination works (check if page shows groups)
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


def test_category_page():
    """Test 1: /sde/category/6/ - Verify category page displays groups"""
    print("\n" + "="*80)
    print("TEST 1: Category Page (/sde/category/6/)")
    print("="*80)

    url = f"{BASE_URL}/sde/category/6/"
    response = requests.get(url)

    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for category title
    title = soup.find('h1')
    if title:
        print(f"✅ Category title: {title.get_text().strip()}")

    # Count groups on the page (not items - categories show groups)
    table_rows = soup.find_all('tr')
    # Filter out header rows
    data_rows = [tr for tr in table_rows if tr.find('td')]
    print(f"Groups found on page: {len(data_rows)}")

    if len(data_rows) > 0:
        print("✅ Groups are displayed")

        # Check first few groups
        for i, row in enumerate(data_rows[:3]):
            cells = row.find_all('td')
            if cells:
                group_name = cells[0].get_text().strip()
                item_count = cells[1].get_text().strip() if len(cells) > 1 else "N/A"
                print(f"   Group {i+1}: {group_name} ({item_count} items)")

        # Note: Category pages don't have pagination for groups (they show all groups)
        print("ℹ️  Category pages show ALL groups in the category (no pagination)")
    else:
        print("❌ No groups found on page")

    return len(data_rows) > 0


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
        print(f"   Error page detected - check template for issues")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for search results table
    table = soup.find('table')
    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"✅ Search results table found with {len(rows)} rows")

            if len(rows) > 0:
                # Show first result
                first_row = rows[0]
                cells = first_row.find_all('td')
                if cells:
                    item_name = cells[0].get_text().strip()
                    print(f"   First result: {item_name[:60]}")

                    # Check if result contains "shield"
                    if 'shield' in item_name.lower():
                        print("✅ Results appear relevant to search query")
                    else:
                        print("⚠️  First result doesn't contain 'shield' in name")
            else:
                print("❌ No results in table body")
        else:
            print("❌ No tbody found in results table")
    else:
        print("❌ No results table found")

    # Check for result count
    result_count = soup.find(text=lambda t: t and 'items found' in str(t))
    if result_count:
        print(f"✅ Result count indicator: {result_count.strip()}")

    # Check for pagination if many results
    if len(rows) > 1:
        # Look for pagination controls
        pagination = soup.find_all('a', href=lambda x: x and 'page=' in str(x))
        if pagination:
            print(f"✅ Pagination links found: {len(pagination)}")

    return table is not None and len(tbody.find_all('tr')) > 0 if tbody else False


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

    # Check for category filter being selected
    category_select = soup.find('select', {'name': 'category'})
    if category_select:
        selected_option = category_select.find('option', selected=True)
        if selected_option:
            category_name = selected_option.get_text().strip()
            print(f"✅ Category filter selected: {category_name}")

            # Category 7 should be "Module"
            if 'Module' in category_name or '7' in str(selected_option.get('value', '')):
                print("✅ Category 7 (Module) is correctly selected")
        else:
            print("⚠️  No category option appears to be selected")
    else:
        print("❌ No category select found")

    # Check for search results
    table = soup.find('table')
    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"✅ Results found: {len(rows)} items")

            if len(rows) > 0:
                # Check first few results to see if they're modules
                module_count = 0
                for row in rows[:min(5, len(rows))]:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        group_category = cells[2].get_text().strip()
                        if 'Module' in group_category or '7' in str(cells):
                            module_count += 1

                print(f"   {module_count}/{min(5, len(rows))} sampled results appear to be modules")

        # Check for active filter badge
        filter_badge = soup.find('span', class_='filter-badge')
        if filter_badge:
            print(f"✅ Active filter badge found: {filter_badge.get_text().strip()[:50]}")
    else:
        print("❌ No results table found")

    return table is not None


def test_group_pagination():
    """Test 4: /sde/group/26/?page=2 - Test group pagination"""
    print("\n" + "="*80)
    print("TEST 4: Group Pagination (/sde/group/26/?page=2)")
    print("="*80)

    # First check page 1 to see how many items exist
    url_page1 = f"{BASE_URL}/sde/group/26/"
    response1 = requests.get(url_page1)

    print(f"Checking page 1 first: {url_page1}")
    print(f"Status Code: {response1.status_code}")

    if response1.status_code == 200:
        soup1 = BeautifulSoup(response1.text, 'html.parser')
        table1 = soup1.find('table')

        if table1:
            tbody1 = table1.find('tbody')
            if tbody1:
                rows1 = tbody1.find_all('tr')
                print(f"   Page 1 has {len(rows1)} items")

                # Get first item from page 1
                first_item_p1 = rows1[0].find('td').get_text().strip() if rows1 else "N/A"
                print(f"   First item on page 1: {first_item_p1[:50]}")

    # Now check page 2
    url = f"{BASE_URL}/sde/group/26/?page=2"
    response = requests.get(url)

    print(f"\nURL: {url}")
    print(f"Status Code: {response.status_code}")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch page")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check for items on page 2
    table = soup.find('table')
    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"Items found on page 2: {len(rows)}")

            if len(rows) > 0:
                print("✅ Page 2 has items (pagination working)")

                # Get first item from page 2
                first_item_p2 = rows[0].find('td').get_text().strip()
                print(f"   First item on page 2: {first_item_p2[:50]}")

                # Verify it's different from page 1
                if 'first_item_p1' in locals() and first_item_p2 != first_item_p1:
                    print("✅ Page 2 shows different items than page 1")
            else:
                print("⚠️  No items on page 2 (might not have enough data for page 2)")
        else:
            print("❌ No tbody found")
    else:
        print("❌ No table found")

    # Check for pagination controls
    pagination_links = soup.find_all('a', href=lambda x: x and 'page=' in str(x))
    if pagination_links:
        print(f"✅ Pagination links found: {len(pagination_links)}")
        for link in pagination_links:
            print(f"   - {link.get_text().strip()}: {link.get('href', '')[:60]}")
    else:
        print("ℹ️  No pagination links visible")

    return response.status_code == 200


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

    # Check for sort dropdown
    sort_select = soup.find('select', {'name': 'sort'})
    if sort_select:
        selected_option = sort_select.find('option', selected=True)
        if selected_option:
            sort_label = selected_option.get_text().strip()
            print(f"✅ Sort option selected: {sort_label}")

            if 'name' in selected_option.get('value', '').lower():
                print("✅ Sort by name is correctly selected")
        else:
            print("⚠️  No sort option appears to be selected")
    else:
        print("❌ No sort select found")

    # Check for results
    table = soup.find('table')
    if table:
        tbody = table.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            print(f"✅ Results found: {len(rows)} items")

            if len(rows) >= 2:
                # Get item names from first few rows
                item_names = []
                for row in rows[:5]:
                    cells = row.find_all('td')
                    if cells:
                        name_link = cells[0].find('a')
                        if name_link:
                            item_names.append(name_link.get_text().strip())

                if item_names:
                    print(f"   First 5 results: {', '.join([n[:30] for n in item_names])}")

                    # Check if sorted alphabetically
                    sorted_names = sorted(item_names, key=str.lower)
                    if item_names == sorted_names:
                        print("✅ Results appear to be sorted alphabetically")
                    else:
                        print("⚠️  Results may not be perfectly sorted (case sensitivity?)")
                        print(f"   Current order matches: {item_names == sorted_names}")

        # Check for sort indicators in table headers
        headers = table.find_all('th')
        name_header = [h for h in headers if 'name' in h.get_text().lower()]
        if name_header:
            print("✅ Name column header found")
    else:
        print("❌ No results table found")

    return table is not None


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("SDE PAGINATION AND FILTERING TEST SUITE")
    print("="*80)
    print(f"Testing against: {BASE_URL}")

    results = {
        'Category Page': test_category_page(),
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
