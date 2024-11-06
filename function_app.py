import azure.functions as func
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlencode
import logging
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

ENV = {
    "MAILGUN_API": os.environ.get("MAILGUN_API"),
    "MAIL_FROM": os.environ.get("MAIL_FROM"),
    "MAIL_TO": os.environ.get("MAIL_TO"),
    "MAILGUN_API_KEY": os.environ.get("MAILGUN_API_KEY"),
    "JOB_URL": os.environ.get("JOB_URL"),
    "INTERNSHIP_URL": os.environ.get("INTERNSHIP_URL"),
    "HACKATHON_URL": os.environ.get("HACKATHON_URL"),
}

# app = func.FunctionApp()
# @app.schedule(
#     schedule="0 * * * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False
# )
# def timer_trigger(myTimer: func.TimerRequest) -> None:
#     if myTimer.past_due:
#         logging.info("The timer is past due!")

#     logging.info("Python timer trigger function executed.")


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def get_jobs(url: str) -> set:
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        logging.info(f"Error fetching {url}: {e}")
        return set()

    soup = BeautifulSoup(response.text, "html.parser")
    links = set()

    h4_elements = soup.select("h4.wp-block-heading")
    heading = soup.select_one("h1.elementor-heading-title.elementor-size-default")
    heading_text = heading.text.strip() if heading else "No heading found"
    time_text = (
        soup.select_one("time").text.strip()
        if soup.select_one("time")
        else "No time available"
    )

    for element in h4_elements:
        job = element.find("a")
        if job and job.get("href"):
            links.add((heading_text, job.get("href"), time_text))

    return links


def process(url: str) -> list:
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        logging.info(f"Error fetching {url}: {e}")
        return set()

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.select("a")
    link_list = set()
    jobs = set()

    for link in links:
        href = link.get("href")
        if href and href.startswith(url):
            link_list.add(href)

    job_links = [get_jobs(link) for link in link_list]
    for job in job_links:
        jobs.update(job)

    return list(jobs)


def send_mail(data):
    table_html = f"""
        <h2 style="color: red;">Jobs</h2>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th style="color: purple;">Job Title</th>
            <th style="color: purple;">Job URL</th>
            <th style="color: purple;">Posted On</th>
        </tr>
        {''.join(f"<tr><td>{d[0]}</td><td><a href='{d[1]}' style='color: blue;'>{d[1]}</a></td><td>{d[2]}</td></tr>" 
        for d in data['jobs'])}
        </table>
    """ if data.get('jobs') else '' 

    table_html = table_html + f"""
        <h2 style="color: red;">Internships</h2>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th style="color: purple;">Job Title</th>
            <th style="color: purple;">Job URL</th>
            <th style="color: purple;">Posted On</th>
        </tr>
        {''.join(f"<tr><td>{d[0]}</td><td><a href='{d[1]}' style='color: blue;'>{d[1]}</a></td><td>{d[2]}</td></tr>" 
        for d in data['internships'])}
        </table>
    """ if data.get('internships') else ''
    
    table_html = table_html + f"""
        <h2 style="color: red;">Hackathons</h2>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th style="color: purple;">Job Title</th>
            <th style="color: purple;">Job URL</th>
            <th style="color: purple;">Posted On</th>
        </tr>
        {''.join(f"<tr><td>{d[0]}</td><td><a href='{d[1]}' style='color: blue;'>{d[1]}</a></td><td>{d[2]}</td></tr>" 
        for d in data['hackathons'])}
        </table>
    """ if data.get('hackathons') else ''

    url = f"{os.environ.get('MAILGUN_API')}?{urlencode({'from': os.environ.get('MAIL_FROM')})}"
    data = {
        "to": os.environ.get("MAIL_TO"),
        "subject": "Jobs Notifications ",
        "html": table_html,
    }

    try:
        response = requests.post(
            url, auth=("api", os.environ.get("MAILGUN_API_KEY")), data=data
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return table_html
    except requests.exceptions.RequestException as e:
        logging.info(f"Error sending mail: {e}")



@app.timer_trigger(schedule="0 0 10 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    urls = {
        "jobs": os.environ.get("JOB_URL"),
        "internships": os.environ.get("INTERNSHIP_URL"),
        "hackathons": os.environ.get("HACKATHON_URL")
    }


    ans = {k: process(v) for k, v in urls.items()}

    ans = send_mail(ans)
    logging.info("Mail sent successfully")