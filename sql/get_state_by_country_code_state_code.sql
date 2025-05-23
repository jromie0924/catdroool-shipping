select
  s.iso2
from countries c
inner join states s on s.country_id = c.id
where
  upper(c.iso2) = %s
  and upper(s.iso2) = %s