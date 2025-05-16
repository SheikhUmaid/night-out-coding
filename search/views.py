import os
import csv
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.utils.timezone import now
from django.http import HttpResponse
from django.conf import settings



def is_domain_active(url):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def is_shopify_store(url):
    try:
        response = requests.get(url, timeout=5)
        return 'cdn.shopify.com' in response.text or 'Shopify' in response.text
    except:
        return False

def loads_within_5_seconds(url):
    try:
        response = requests.get(url, timeout=5)
        return response.elapsed.total_seconds() <= 5
    except:
        return False

def extract_email_from_site(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        emails = set()
        for word in text.split():
            if '@' in word and '.' in word:
                emails.add(word.strip())

        if emails:
            return ', '.join(emails)

        for a in soup.find_all('a', href=True):
            if 'contact' in a['href']:
                contact_url = urljoin(url, a['href'])
                response = requests.get(contact_url, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text()
                for word in text.split():
                    if '@' in word and '.' in word:
                        emails.add(word.strip())
                if emails:
                    return ', '.join(emails)
    except:
        return ''
    return ''

def google_search_urls(query, count=10):
    try:
        from googlesearch import search
        return list(search(query, num_results=count))
    except ImportError:
        return []

def dashboard(request):
    context = {}

    if request.method == 'POST':
        if 'fetch_websites' in request.POST:
            country = request.POST.get('country')
            city = request.POST.get('city')
            industry = request.POST.get('industry')
            count = int(request.POST.get('count', 50))

            query = f"{industry} in {city}, {country}"
            urls = google_search_urls(query, count=count)

            websites = []
            for i, full_url in enumerate(urls):
                root = urlparse(full_url).netloc.replace('www.', '')
                websites.append({'Name': f"{industry} {i+1}", 'Website': root})

            filename = f"websites_{now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(settings.MEDIA_ROOT, filename)
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Name', 'Website'])
                writer.writeheader()
                writer.writerows(websites)

            context['results'] = websites
            context['csv_download'] = f"/{filename}"

        elif 'filter_websites' in request.POST and request.FILES.get('csv_file'):
            file = request.FILES['csv_file']
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(file.name, file)
            filepath = os.path.join(settings.MEDIA_ROOT, filename)

            is_active = 'is_active' in request.POST
            is_shopify = 'is_shopify' in request.POST
            loads_fast = 'loads_fast' in request.POST

            filtered = []
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = 'http://' + row['Website']
                    if is_active and not is_domain_active(url):
                        continue
                    if is_shopify and not is_shopify_store(url):
                        continue
                    if loads_fast and not loads_within_5_seconds(url):
                        continue
                    filtered.append(row)

            out_file = f"filtered_{now().strftime('%Y%m%d_%H%M%S')}.csv"
            out_path = os.path.join(settings.MEDIA_ROOT, out_file)
            with open(out_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Name', 'Website'])
                writer.writeheader()
                writer.writerows(filtered)

            context['results'] = filtered
            context['csv_download'] = f"/{out_file}"

        elif 'fetch_emails' in request.POST and request.FILES.get('csv_file_email'):
            file = request.FILES['csv_file_email']
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(file.name, file)
            filepath = os.path.join(settings.MEDIA_ROOT, filename)

            results = []
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = 'http://' + row['Website']
                    email = extract_email_from_site(url)
                    results.append({'Website': row['Website'], 'Email': email})

            out_file = f"emails_{now().strftime('%Y%m%d_%H%M%S')}.csv"
            out_path = os.path.join(settings.MEDIA_ROOT, out_file)
            with open(out_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Website', 'Email'])
                writer.writeheader()
                writer.writerows(results)

            context['results'] = results
            context['csv_download'] = f"/{out_file}"
            

    return render(request, 'index.html', context)