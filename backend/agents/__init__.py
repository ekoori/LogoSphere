"""AI personas for LogoSphere's demo spheres.

Twenty demo accounts (famous names playing everyday neighbours, flagged
users.is_agent) act inside the demo spheres (spheres.is_demo). They react to
what real members do - confirm acceptances, follow back, write their side of
an exchange, offer help with a new need - and to each other within "ripple"
credits that real activity creates. When nobody real is around they are quiet.

  config.py      settings (agents.env)
  personas.py    who they are (personas.json)
  writer.py      Claude writes their words (structured output, guardrails)
  images.py      OpenAI draws opening banners
  platform.py    the LogoSphere API, called as a persona
  store.py       queue, settings, log (Cassandra tables)
  rules.py       what to do about what was seen (pure functions)
  director.py    the loop: observe, plan, act
  run.py         the systemd entry point

Design: docs/plans/2026-11-19-demo-spheres-and-personas-design.md
"""
