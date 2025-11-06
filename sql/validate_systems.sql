SELECT solarSystemId, name, regionId
FROM SolarSystems
WHERE
    name NOT REGEXP '^[AMU] [0-9]{3,4}$'
AND name NOT REGEXP '^[A-Z0-9]{3}-[A-Z0-9]{3}$'
AND name NOT REGEXP '^[A-Z0-9]:[A-Z0-9]{4}$'
AND name NOT REGEXP '^[A-Z0-9]\.[A-Z0-9]{3}\.[A-Z0-9]{3}$'
AND name NOT REGEXP '^[A-Z0-9]{3}\|[A-Z0-9]{3}$'
AND name NOT REGEXP '^[A-Z][a-z]+$'
AND name NOT REGEXP '^AD[0-9]{3}$'
AND name NOT REGEXP '^V-[0-9]{3}$';

SELECT
    COUNT(*) AS Total_SolarSystems,

    -- Disjoint classes (anchored)
    SUM(name REGEXP '^[AMU] [0-9]{3,4}$')                       AS blackhole,
    SUM(name REGEXP '^[A-Z0-9]{3}-[A-Z0-9]{3}$')                AS Dash_XXX_XXX,
    SUM(name REGEXP '^[A-Z0-9]:[A-Z0-9]{4}$')                   AS Colon_X_XXXX,
    SUM(name REGEXP '^[A-Z0-9]\.[A-Z0-9]{3}\.[A-Z0-9]{3}$')     AS Dot_X_XXX_XXX,
    SUM(name REGEXP '^[A-Z0-9]{3}\|[A-Z0-9]{3}$')               AS Pipe_XXX_XXX,
    SUM(name REGEXP '^[A-Z][a-z]+$')                            AS Proper_Nouns,
    SUM(name REGEXP '^AD[0-9]{3}$')                             AS AD_prefix,
    SUM(name REGEXP '^V-[0-9]{3}$')                             AS V_prefix,

    -- Sum of all matches (should equal Total - Unclassified if disjoint)
    (
      SUM(name REGEXP '^[AMU] [0-9]{3,4}$') +
      SUM(name REGEXP '^[A-Z0-9]{3}-[A-Z0-9]{3}$') +
      SUM(name REGEXP '^[A-Z0-9]:[A-Z0-9]{4}$') +
      SUM(name REGEXP '^[A-Z0-9]\.[A-Z0-9]{3}\.[A-Z0-9]{3}$') +
      SUM(name REGEXP '^[A-Z0-9]{3}\|[A-Z0-9]{3}$') +
      SUM(name REGEXP '^[A-Z][a-z]+$') +
      SUM(name REGEXP '^AD[0-9]{3}$') +
      SUM(name REGEXP '^V-[0-9]{3}$')
    ) AS Sum_of_All_Matches,

    -- Anything that matched none of the above
    (COUNT(*) -
      (
        SUM(name REGEXP '^[AMU] [0-9]{3,4}$') +
        SUM(name REGEXP '^[A-Z0-9]{3}-[A-Z0-9]{3}$') +
        SUM(name REGEXP '^[A-Z0-9]:[A-Z0-9]{4}$') +
        SUM(name REGEXP '^[A-Z0-9]\.[A-Z0-9]{3}\.[A-Z0-9]{3}$') +
        SUM(name REGEXP '^[A-Z0-9]{3}\|[A-Z0-9]{3}$') +
        SUM(name REGEXP '^[A-Z][a-z]+$') +
        SUM(name REGEXP '^AD[0-9]{3}$') +
        SUM(name REGEXP '^V-[0-9]{3}$')
      )
    ) AS Unclassified
FROM SolarSystems;