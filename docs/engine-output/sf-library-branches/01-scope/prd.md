---
generated_by:
  backend: vultr
  model: glm-5.3
  at: '2026-09-27T17:05:52.159717+00:00'
---
# Global PRD

Brief: `brief.md`

## Personas

- **p1** SF resident or visitor seeking a library branch with free Wi-Fi and open hours.
- **p2** Researcher compiling a verified dataset of SFPL branches with sourced values.

## Jobs to be done

- **j1** Find an SFPL branch near me that is open now and offers free Wi-Fi.
- **j2** Compile every SFPL branch with address, weekly hours, and Wi-Fi status, each value evidenced.

## Requirements

- **r1** List every SFPL branch with address, weekly opening hours, and free Wi-Fi yes/no, each value with a cited source.
- **r2** Treat sfpl.org as the primary publisher for branches, hours, and Wi-Fi; its values need no second source.
- **r3** Cross-check branch addresses against data.sfgov.org as a secondary publisher; flag mismatches for review.
- **r4** Use only public, read-only sources; jurisdiction San Francisco, California, USA; completion when every branch has all three values evidenced.

## Definition of done

- Share of SFPL branches listed with address, weekly opening hours, and free Wi-Fi yes/no >= 1 [basis: proposed] (per-entity ratio: 1) — The stated numeric threshold lacks a matching brief or human quote.; At $5.00, feasibility and elapsed run time need validation after source discovery.
- Share of listed values (address, hours, Wi-Fi) with a cited source >= 1 [basis: proposed] (per-entity ratio: 1) — The stated numeric threshold lacks a matching brief or human quote.; At $5.00, feasibility and elapsed run time need validation after source discovery.
- Share of branch addresses cross-checked against data.sfgov.org >= 1 [basis: proposed] (per-entity ratio: 1) — The stated numeric threshold lacks a matching brief or human quote.; At $5.00, feasibility and elapsed run time need validation after source discovery.
- Share of values sourced from non-public or non-read-only sources <= 0 [basis: proposed] — The stated numeric threshold lacks a matching brief or human quote.; At $5.00, feasibility and elapsed run time need validation after source discovery.
- Number of branches listed that are missing from the final output <= 0 [basis: proposed] — The stated numeric threshold lacks a matching brief or human quote.; At $5.00, feasibility and elapsed run time need validation after source discovery.

## Authority policy

- San Francisco Public Library official website [primary]: Brief names sfpl.org as primary publisher for branches, hours, and Wi-Fi.
- San Francisco open data portal (branch addresses cross-check) [secondary]: Brief names data.sfgov.org as secondary cross-check for branch addresses only.
