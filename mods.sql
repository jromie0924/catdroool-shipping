-- scratchpad file

select
  cit.*
from countries c
inner join cities cit on cit.country_id = c.id
where
  c.name = 'Italy'
  and cit.name ilike 't%'
order by cit.name asc