# YouTube Cookie Export Guide

## Why You're Getting the Bot Detection Error

The error "Sign in to confirm you're not a bot" indicates that YouTube has detected automated access and is requiring authentication. This happens when:

1. **Cookies are expired** - YouTube cookies typically expire after a few days/weeks
2. **Cookies are invalid** - The authentication session has ended
3. **YouTube has updated their security** - New bot detection measures

## How to Export Fresh Cookies

### Method 1: Using Browser Extensions (Recommended)

#### Chrome/Edge:
1. Install the "Get cookies.txt" extension
2. Go to YouTube and make sure you're logged in
3. Click the extension icon
4. Click "Export" to download cookies.txt
5. Replace the existing file in your `cookies/` folder

#### Firefox:
1. Install the "cookies.txt" extension
2. Go to YouTube and make sure you're logged in
3. Click the extension icon
4. Click "Export" to download cookies.txt
5. Replace the existing file in your `cookies/` folder

### Method 2: Manual Export (Advanced)

1. Go to YouTube and log in
2. Open Developer Tools (F12)
3. Go to Application/Storage tab
4. Find Cookies section
5. Right-click on youtube.com cookies
6. Export as Netscape format
7. Save as `cookies/BrandedXMusic.txt`

### Method 3: Using Python Script

```python
import browser_cookie3
import http.cookiejar

# Export cookies from Chrome
cookies = browser_cookie3.chrome(domain_name='.youtube.com')

# Save in Netscape format
with open('cookies/BrandedXMusic.txt', 'w') as f:
    f.write('# Netscape HTTP Cookie File\n')
    f.write('# https://curl.haxx.se/rfc/cookie_spec.html\n\n')
    
    for cookie in cookies:
        f.write(f'{cookie.domain}\tTRUE\t{cookie.path}\t'
                f'{"TRUE" if cookie.secure else "FALSE"}\t{cookie.expires}\t'
                f'{cookie.name}\t{cookie.value}\n')
```

## Important Notes

1. **Always export cookies while logged into YouTube**
2. **Use a real browser session** (not incognito/private mode)
3. **Cookies expire quickly** - you may need to refresh them weekly
4. **Use the same browser** you normally use for YouTube
5. **Don't share cookies** - they contain your authentication tokens

## Testing Your Cookies

After updating cookies, test them using the provided test script:

```bash
# In your Docker container
python3 test_cookies.py
```

## Troubleshooting

### If cookies still don't work:

1. **Clear browser cookies** and log in again
2. **Try a different browser** (Chrome, Firefox, Edge)
3. **Check if YouTube is blocking your IP** (try from different location)
4. **Verify the cookie file format** - should start with "# Netscape HTTP Cookie File"
5. **Check file permissions** - ensure the container can read the file

### Common Issues:

- **Permission denied**: Check file permissions in Docker
- **File not found**: Verify the cookies directory path
- **Invalid format**: Ensure cookies are in Netscape format
- **Expired cookies**: Export fresh cookies from browser

## Docker-Specific Notes

Since you're using Docker:

1. **Volume mounting**: Ensure cookies directory is properly mounted
2. **File permissions**: Container user needs read access to cookies
3. **Path resolution**: Use absolute paths in Docker environment
4. **Container restart**: You may need to restart after updating cookies

## Quick Fix Commands

```bash
# Test current cookies
python3 test_cookies.py

# Check cookie file status
ls -la cookies/

# Verify file contents
head -5 cookies/BrandedXMusic.txt

# Check Docker container logs
docker logs <container_name>
```