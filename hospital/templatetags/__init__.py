from django import template

register = template.Library()


@register.filter
def has_role(roles, role):
    return role in (roles or [])


@register.filter
def any_role(roles, wanted):
    wanted_list = [r.strip() for r in (wanted or "").split(",") if r.strip()]
    rset = set(roles or [])
    return any(w in rset for w in wanted_list)


@register.filter
def in_dept(depts, dept):
    return (dept or "").lower() in {d.lower() for d in (depts or [])}
