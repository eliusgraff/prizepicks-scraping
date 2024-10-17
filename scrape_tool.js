const puppeteer = require('puppeteer');
const fs = require('fs');

const save_file = "scrape_data.json"

const url = 'https://api.prizepicks.com/projections?league_id=9&per_page=250&single_stat=true&in_game=false&state_code=OR&game_mode=prizepools';

// pip install puppeteer (if you don't have it already)
// To Run: node scrape.js 

(async () => {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    try {
        // Add custom headers if needed
        await page.setExtraHTTPHeaders({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
            'Accept': 'application/json',
        });

        // Navigate to the URL
        await page.goto(url, { waitUntil: 'networkidle2' });

        // Get the response content
        const responseBody = await page.evaluate(() => document.body.innerText);

        // Attempt to parse the response as JSON
        const data = JSON.parse(responseBody); 

        // Pretty-print the JSON data
        const prettyJSON = JSON.stringify(data, null, 4);

        // Save the pretty JSON to a file
        fs.writeFileSync(save_file, prettyJSON);

        console.log('Data has been saved to ' + save_file);
    } catch (error) {
        console.error('Error fetching data:', error.message);
    } finally {
        await browser.close();
    }
})();
