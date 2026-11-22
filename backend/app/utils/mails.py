"""The letters LogoSphere sends: plain words first, the same as HTML.

What members typed (names, titles) is escaped and loses its links, so nobody
can post a link into someone else's inbox through LogoSphere.
"""
import re
from collections import namedtuple
from html import escape

Letter = namedtuple('Letter', 'subject text html')

_LINK = re.compile(r'(?i)\b(?:[a-z][a-z0-9+.-]*://|www\.)\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}/\S*')
TEXT_MAX = 300


def clean(text, most=TEXT_MAX):
    """Something a member wrote, safe to mail: one line, no links, not too long."""
    line = _LINK.sub('(link removed)', ' '.join(str(text or '').split()))
    return line if len(line) <= most else line[:most - 1].rstrip() + '…'


def letter(subject, paragraphs, button=None, why='', links=()):
    """`button` and each of `links` are (label, url)."""
    text = [subject, *paragraphs]
    if button:
        text.append(f'{button[0]}:\n{button[1]}')
    foot = [line for line in [why, *(f'{label}: {url}' for label, url in links)] if line]
    if foot:
        text.append('--\n' + '\n'.join(foot))

    body = ''.join(f'<p style="margin:0 0 14px">{escape(p)}</p>' for p in paragraphs)
    if button:
        body += (f'<p style="margin:22px 0"><a href="{escape(button[1])}" style="display:inline-block;padding:12px 22px;'
                 f'background:#46583a;color:#fdfaf2;border-radius:24px;text-decoration:none;font-weight:bold">'
                 f'{escape(button[0])}</a></p>'
                 f'<p style="margin:0 0 14px;font-size:13px;color:#54593f">Or copy this into your browser:<br>'
                 f'<span style="word-break:break-all">{escape(button[1])}</span></p>')
    small = [escape(why)] if why else []
    small += [f'<a href="{escape(url)}" style="color:#54593f">{escape(label)}</a>' for label, url in links]
    html = ('<!doctype html><html lang="en"><body style="margin:0;padding:24px 12px;background:#f3ecda;color:#232a1d;'
            'font-family:Arial,Helvetica,sans-serif;font-size:17px;line-height:1.5">'
            '<div style="max-width:520px;margin:0 auto;padding:26px;background:#fdfaf2;border-radius:16px">'
            '<p style="margin:0 0 18px;font-weight:bold;color:#46583a">LogoSphere</p>'
            f'<h1 style="margin:0 0 14px;font-size:22px;line-height:1.3">{escape(subject)}</h1>{body}'
            f'<p style="margin:22px 0 0;font-size:13px;color:#54593f">{"<br>".join(small)}</p>'
            '</div></body></html>')
    return Letter(subject, '\n\n'.join(text), html)


def finish_sign_up(url, hours):
    return letter(
        'Finish joining LogoSphere',
        ['Someone, hopefully you, asked to join LogoSphere with this email address.',
         f'Press the button to choose your password. It works once, for {hours} hours.',
         "If it wasn't you, do nothing: no account is made."],
        ('Choose my password', url))


def have_account(url):
    return letter(
        'You already have a LogoSphere account',
        ['Someone, hopefully you, asked to join with this email address, and it has an account already.',
         'Log in with it. If you forgot the password, press "Forgot your password?" there.',
         "If it wasn't you, do nothing: nothing has changed."],
        ('Log in', url))


def reset_password(url, hours):
    return letter(
        'Choose a new LogoSphere password',
        ['Someone, hopefully you, asked for a new password for your account.',
         f'The button works once, for {hours} hours. Afterwards you are signed out everywhere and log in again.',
         "If it wasn't you, do nothing: your password stays as it is."],
        ('Choose a new password', url))


def confirm_address(url, hours):
    return letter(
        'Confirm your email for LogoSphere',
        ['Press the button to confirm that this address is yours. Email notifications start only after that.',
         f'It works once, for {hours} hours.',
         "If you don't use LogoSphere, do nothing: nothing will be sent."],
        ('Confirm my email', url))


def password_changed(url):
    return letter(
        'Your LogoSphere password was changed',
        ['The password for your account was just changed.',
         'If that was you, there is nothing to do.',
         "If it wasn't, choose a new one now with \"Forgot your password?\" on the log in page."],
        ('Go to log in', url))


def news(subject, message, url, stop_url, settings_url):
    return letter(
        subject, [clean(message)], ('See it on LogoSphere', url),
        why='You get this because you turned on email notifications.',
        links=(('Choose what is emailed', settings_url), ('Stop all notification emails', stop_url)))
