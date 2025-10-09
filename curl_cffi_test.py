from curl_cffi import requests as r

if __name__ == "__main__":
    ep = "https://api.prizepicks.com/projections?league_id=7&per_page=20&single_stat=true&game_mode=pickem"
    for _ in range(10):
        wp = r.get(ep, impersonate='chrome')
        print(wp)