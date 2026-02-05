/**
 * ORRG Command Center - Shared Validation Code
 * 
 * This JavaScript file contains all shared validation logic used by:
 * - Status bar (input panel)
 * - Single Range Ring validator (Help tab)
 * - Reverse Range Ring validator (Help tab)
 * 
 * The code is injected into each widget via Python's components.html()
 * Placeholders like {{COUNTRIES_JSON}} are replaced by Python at runtime.
 */

// ================================================================
// SHARED VALIDATION CODE - ORRG_VALIDATION object
// ================================================================
const ORRG_VALIDATION = {
    // Valid options for command parsing
    validVerbs: ['generate', 'create', 'build', 'show'],
    validReverseTypes: ['reverse range ring', 'reverse ring', 'launch envelope', 'reverse range'],
    validSingleTypes: ['single range ring', 'single ring', 'range ring'],
    validFromPreps: ['from', 'within', 'inside', 'for', 'between'],
    validMinimumTypes: ['minimum range ring', 'minimum distance', 'min distance', 'min range'],
    validMultipleTypes: ['multiple range rings', 'multiple range ring', 'multiple rings'],
    validCustomPoiTypes: ['custom poi', 'custom point', 'point of interest', 'poi'],
    validCustomPoiUnits: ['km', 'mi'],
    validMultipleUnits: ['km', 'mi', 'nm'],
    validMinimumPreps: ['between', 'from'],
    validMinimumTargets: ['and', 'to'],
    validTargetPreps: ['against', 'to', 'toward', 'towards'],

    // Launch trajectory
    validTrajectoryTypes: ['launch trajectory', 'trajectory', 'flight path', 'launch path'],
    validTrajectoryFromPreps: ['from'],
    validTrajectoryToPreps: ['to', 'toward', 'towards'],
    
    // These are populated by Python at injection time
    validCountries: {{COUNTRIES_JSON}},
    validCities: {{CITIES_JSON}},
    countriesDisplay: {{COUNTRIES_DISPLAY_JSON}},
    citiesDisplay: {{CITIES_DISPLAY_JSON}},
    
    // ============================================================
    // Shared status messages (used by status bar and validators)
    // ============================================================
    messages: {
        // Empty/typing states
        empty: 'Enter a command above to execute',
        typing: 'Keep typing your command...',
        
        // Valid states
        valid: 'Query looks valid!',
        validHint: 'Click Execute to proceed',
        
        // Warning states
        fuzzy: 'Query may work, but check ⚠ items for exact format',
        attention: 'Some fields need attention',
        attentionHint: function(toolName) {
            return 'Check items in Help under ' + toolName + ' marked with ✗ or ⚠';
        },
        
        // Validator-specific messages
        validatorValid: '✅ Query looks valid! Click Execute to proceed.',
        validatorAttention: '⚠️ Some fields need attention. Check the items marked with ✗ or ⚠',
        validatorFuzzy: '⚠️ Query may work, but check ⚠ items for exact format.',
        validatorPending: 'Type your command above to see validation...',
        
        // Format hints
        reverseFormat: 'Format: Generate a reverse range ring from [Country] against [City]',
        singleFormat: 'Format: Generate a single range ring from [Country]',
        minimumFormat: 'Format: Calculate minimum distance between [Location A] and [Location B]',
        multipleFormat: 'Format: Generate multiple range rings from [Country] at [distances] [unit]. The respective missile names are [names].',
        
        // Unrecognized/query states
        unrecognized: 'Command pattern not recognized',
        query: 'Query detected (not a task command)',
        queryHint: 'Will be processed as a question',
        
        // Helper functions
        seeHelp: function(toolName) {
            return 'See Help → ' + toolName;
        },
        
        // Redirect messages
        reverseRedirect: 'This looks like a Reverse Range Ring command. See Reverse Range Ring tab.',
        singleRedirect: 'This looks like a Single Range Ring command. See Single Range Ring tab.',
        minimumRedirect: 'This looks like a Minimum Range Ring command. See Minimum Range Ring tab.',
        customPoiRedirect: 'This looks like a Custom POI command. See Custom POI tab.',
        trajectoryRedirect: 'This looks like a Launch Trajectory command. See Launch Trajectory tab.'
    },
    
    // ============================================================
    // Fuzzy match function (single best match)
    // ============================================================
    fuzzyMatch: function(input, options) {
        if (!input) return null;
        const lower = input.toLowerCase().trim();
        
        // Exact match first
        if (options.includes(lower)) return lower;
        
        // Prefix match
        const prefixMatch = options.find(opt => opt.startsWith(lower));
        if (prefixMatch) return prefixMatch;
        
        // Word-based match
        for (const opt of options) {
            const words = opt.split(/[\s,]+/);
            for (const word of words) {
                if (word.startsWith(lower) || lower.startsWith(word)) {
                    return opt;
                }
            }
        }
        
        // Contains match
        const containsMatch = options.find(opt => opt.includes(lower) || lower.includes(opt));
        return containsMatch || null;
    },
    
    // ============================================================
    // Get fuzzy matches for suggestions (returns multiple)
    // ============================================================
    getFuzzyMatches: function(input, displayOptions, maxResults) {
        maxResults = maxResults || 10;
        if (!input || input.length < 1) return displayOptions.slice(0, maxResults);
        const lower = input.toLowerCase().trim();
        
        const scored = displayOptions.map(opt => {
            const optLower = opt.toLowerCase();
            let score = 0;
            
            // Exact match = highest
            if (optLower === lower) score = 100;
            // Starts with = high
            else if (optLower.startsWith(lower)) score = 80;
            // Word in option starts with input
            else {
                const words = optLower.split(/[\s,]+/);
                for (const word of words) {
                    if (word.startsWith(lower)) {
                        score = 70;
                        break;
                    }
                }
            }
            // Contains anywhere
            if (score === 0 && optLower.includes(lower)) score = 50;
            // Input contains option word
            if (score === 0) {
                const words = optLower.split(/[\s,]+/);
                for (const word of words) {
                    if (lower.includes(word) && word.length > 2) {
                        score = 40;
                        break;
                    }
                }
            }
            
            return { opt, score };
        });
        
        return scored
            .filter(s => s.score > 0)
            .sort((a, b) => b.score - a.score)
            .slice(0, maxResults)
            .map(s => s.opt);
    },
    
    // ============================================================
    // Validate Reverse Range Ring command
    // ============================================================
    validateReverse: function(lower) {
        const self = this;
        let verbMatch = self.validVerbs.find(v => lower.startsWith(v));
        let typeMatch = self.validReverseTypes.find(t => lower.includes(t));
        let fromMatch = self.validFromPreps.find(p => {
            const typeEnd = typeMatch ? lower.indexOf(typeMatch) + typeMatch.length : 0;
            return lower.indexOf(' ' + p + ' ', typeEnd) >= 0;
        });
        
        let country = null, city = null, targetPrep = null;
        if (fromMatch && typeMatch) {
            const fromIdx = lower.indexOf(' ' + fromMatch + ' ');
            if (fromIdx >= 0) {
                const afterFrom = lower.substring(fromIdx + fromMatch.length + 2);
                for (const tp of self.validTargetPreps) {
                    const tpIdx = afterFrom.indexOf(' ' + tp + ' ');
                    if (tpIdx >= 0) {
                        targetPrep = tp;
                        country = afterFrom.substring(0, tpIdx).trim();
                        city = afterFrom.substring(tpIdx + tp.length + 2).trim().replace(/\.$/, '');
                        break;
                    }
                }
            }
        }
        
        let countryStatus = country ? (self.validCountries.includes(country.toLowerCase()) ? 'exact' : (self.fuzzyMatch(country, self.validCountries) ? 'fuzzy' : false)) : false;
        let cityStatus = city ? (self.validCities.includes(city.toLowerCase()) ? 'exact' : (self.fuzzyMatch(city, self.validCities) ? 'fuzzy' : false)) : false;
        let countryMatch = countryStatus ? (countryStatus === 'exact' ? country.toLowerCase() : self.fuzzyMatch(country, self.validCountries)) : null;
        let cityMatch = cityStatus ? (cityStatus === 'exact' ? city.toLowerCase() : self.fuzzyMatch(city, self.validCities)) : null;
        
        const allExact = verbMatch && typeMatch && fromMatch && countryStatus === 'exact' && targetPrep && cityStatus === 'exact';
        const allValid = verbMatch && typeMatch && fromMatch && countryMatch && targetPrep && cityMatch;
        const hasFuzzy = countryStatus === 'fuzzy' || cityStatus === 'fuzzy';
        const partialValid = typeMatch || countryMatch || cityMatch;
        
        return {
            allExact, allValid, hasFuzzy, partialValid, toolName: 'Reverse Range Ring',
            verbMatch, typeMatch, fromMatch, targetPrep,
            country, city, countryStatus, cityStatus, countryMatch, cityMatch
        };
    },
    
    // ============================================================
    // Validate Single Range Ring command
    // ============================================================
    validateSingle: function(lower) {
        const self = this;
        let verbMatch = self.validVerbs.find(v => lower.startsWith(v));
        let typeMatch = self.validSingleTypes.find(t => lower.includes(t));
        let fromMatch = null;
        const typeEnd = typeMatch ? lower.indexOf(typeMatch) + typeMatch.length : 0;
        const afterType = lower.substring(typeEnd);
        const fromRegex = /\b(from|for)\b\s*(.*)/;
        const fromRegexMatch = afterType.match(fromRegex);
        if (fromRegexMatch) {
            fromMatch = fromRegexMatch[1];
        }
        
        let country = null;
        if (fromMatch && typeMatch) {
            const fromIdx = lower.indexOf(' ' + fromMatch + ' ');
            if (fromIdx >= 0) {
                country = lower.substring(fromIdx + fromMatch.length + 2).trim().replace(/\.$/, '');
            }
        }
        
        let countryStatus = country ? (self.validCountries.includes(country.toLowerCase()) ? 'exact' : (self.fuzzyMatch(country, self.validCountries) ? 'fuzzy' : false)) : false;
        let countryMatch = countryStatus ? (countryStatus === 'exact' ? country.toLowerCase() : self.fuzzyMatch(country, self.validCountries)) : null;
        
        const allExact = verbMatch && typeMatch && fromMatch && countryStatus === 'exact';
        const allValid = verbMatch && typeMatch && fromMatch && countryMatch;
        const hasFuzzy = countryStatus === 'fuzzy';
        const partialValid = typeMatch || countryMatch;
        
        return {
            allExact, allValid, hasFuzzy, partialValid, toolName: 'Single Range Ring',
            verbMatch, typeMatch, fromMatch, country, countryStatus, countryMatch
        };
    },
    
    // ============================================================
    // Validate Minimum Range Ring command
    // ============================================================
    validateMinimum: function(lower) {
        const self = this;
        let verbMatch = self.validVerbs.find(v => lower.startsWith(v) || lower.startsWith('calculate') || lower.startsWith('compute'));
        let typeMatch = self.validMinimumTypes.find(t => lower.includes(t));
        let prepMatch = self.validMinimumPreps.find(p => lower.includes(' ' + p + ' '));
        
        let locationA = null;
        let locationB = null;
        let targetPrep = null;
        if (prepMatch && typeMatch) {
            const prepIdx = lower.indexOf(' ' + prepMatch + ' ');
            if (prepIdx >= 0) {
                const afterPrep = lower.substring(prepIdx + prepMatch.length + 2);
                const targetMatch = self.validMinimumTargets.find(t => afterPrep.includes(' ' + t + ' '));
                if (targetMatch) {
                    const targetIdx = afterPrep.indexOf(' ' + targetMatch + ' ');
                    targetPrep = targetMatch;
                    locationA = afterPrep.substring(0, targetIdx).trim();
                    locationB = afterPrep.substring(targetIdx + targetMatch.length + 2).trim().replace(/\.$/, '');
                }
            }
        }
        
        const locationOptions = [...self.validCountries, ...self.validCities];
        let locationAStatus = false;
        let locationBStatus = false;
        let locationAMatch = null;
        let locationBMatch = null;
        if (locationA) {
            const locationALower = locationA.toLowerCase();
            if (locationOptions.includes(locationALower)) {
                locationAStatus = 'exact';
                locationAMatch = locationALower;
            } else {
                locationAMatch = self.fuzzyMatch(locationA, locationOptions);
                if (locationAMatch) {
                    locationAStatus = 'fuzzy';
                }
            }
        }
        if (locationB) {
            const locationBLower = locationB.toLowerCase();
            if (locationOptions.includes(locationBLower)) {
                locationBStatus = 'exact';
                locationBMatch = locationBLower;
            } else {
                locationBMatch = self.fuzzyMatch(locationB, locationOptions);
                if (locationBMatch) {
                    locationBStatus = 'fuzzy';
                }
            }
        }
        
        // Check if both locations are the same (invalid - must be different)
        const normalizedA = (locationAMatch || (locationA ? locationA.toLowerCase().trim() : '')).toLowerCase();
        const normalizedB = (locationBMatch || (locationB ? locationB.toLowerCase().trim() : '')).toLowerCase();
        const sameLocation = normalizedA && normalizedB && normalizedA === normalizedB;

        const allExact = (
            verbMatch && typeMatch && prepMatch && (locationAStatus === 'exact') && targetPrep && (locationBStatus === 'exact') && !sameLocation
        );
        const allValid = verbMatch && typeMatch && prepMatch && locationAMatch && targetPrep && locationBMatch && !sameLocation;
        const hasFuzzy = locationAStatus === 'fuzzy' || locationBStatus === 'fuzzy';
        const partialValid = typeMatch || locationAMatch || locationBMatch;
        
        return {
            allExact, allValid, hasFuzzy, partialValid, sameLocation, toolName: 'Minimum Range Ring',
            verbMatch, typeMatch, prepMatch, targetPrep,
            locationA, locationB, locationAStatus, locationBStatus, locationAMatch, locationBMatch
        };
    },

    // ============================================================
    // Validate Multiple Range Ring command
    // ============================================================
    validateMultiple: function(lower) {
        const self = this;
        const verbMatch = self.validVerbs.find(v => lower.startsWith(v));
        const typeMatch = self.validMultipleTypes.find(t => lower.includes(t));
        let fromMatch = null;
        let country = null;
        let distances = [];
        let distancesText = null;
        let unit = null;
        let atMatch = null;
        let missileNames = [];
        let missileNamesText = null;

        if (typeMatch) {
            const typeEnd = lower.indexOf(typeMatch) + typeMatch.length;
            const afterType = lower.substring(typeEnd);
            const fromRegexMatch = afterType.match(/\b(from|for)\b\s*(.*)/);
            if (fromRegexMatch) {
                fromMatch = fromRegexMatch[1];
                const afterFrom = (fromRegexMatch[2] || '').trim();
                if (afterFrom) {
                    const atIdx = afterFrom.indexOf(' at ');
                    if (atIdx >= 0) {
                        atMatch = 'at';
                        country = afterFrom.substring(0, atIdx).trim();
                        const afterAt = afterFrom.substring(atIdx + 4);
                        const distanceSentence = afterAt.split('.')[0].trim();
                        const unitMatch = distanceSentence.match(/(.+?)\s+(km|mi|nm)\b/);
                        if (unitMatch) {
                            distancesText = unitMatch[1].trim();
                            unit = unitMatch[2];
                            distances = distancesText.match(/[\d.]+/g) || [];
                        }
                    } else if (afterFrom.endsWith(' at')) {
                        atMatch = 'at';
                        country = afterFrom.substring(0, afterFrom.length - 3).trim();
                    } else {
                        country = afterFrom.trim();
                    }
                }
            }
        }

        const namesMatch = lower.match(/missile names are (.+)$/);
        if (namesMatch) {
            missileNamesText = namesMatch[1].replace(/\.$/, '').trim();
            missileNames = missileNamesText
                .replace(/\band\b/gi, ',')
                .split(',')
                .map(name => name.trim())
                .filter(Boolean);
        }

        let countryStatus = false;
        let countryMatch = null;
        if (country) {
            const countryLower = country.toLowerCase();
            if (self.validCountries.includes(countryLower)) {
                countryStatus = 'exact';
                countryMatch = countryLower;
            } else {
                countryMatch = self.fuzzyMatch(country, self.validCountries);
                if (countryMatch) {
                    countryStatus = 'fuzzy';
                }
            }
        }

        const distancesStatus = distances.length ? 'exact' : false;
        const unitStatus = unit ? (self.validMultipleUnits.includes(unit) ? 'exact' : 'fuzzy') : false;

        let missileStatus = false;
        if (missileNamesText) {
            if (missileNames.length) {
                if (distances.length && missileNames.length !== distances.length) {
                    missileStatus = 'fuzzy';
                } else {
                    missileStatus = 'exact';
                }
            }
        }

        const allExact = verbMatch && typeMatch && fromMatch && (countryStatus === 'exact')
            && atMatch && distances.length && unit && (missileStatus === 'exact');
        const allValid = verbMatch && typeMatch && fromMatch && countryMatch
            && atMatch && distances.length && unit && missileStatus;
        const hasFuzzy = countryStatus === 'fuzzy' || missileStatus === 'fuzzy';
        const partialValid = typeMatch || countryMatch || distances.length;

        return {
            allExact, allValid, hasFuzzy, partialValid, toolName: 'Multiple Range Ring',
            verbMatch, typeMatch, fromMatch, atMatch,
            country, countryStatus, countryMatch,
            distances, distancesText, unit, unitStatus,
            missileNames, missileNamesText, missileStatus,
            distancesStatus
        };
    },

    // ============================================================
    // Validate Launch Trajectory command (syntactic)
    // Examples:
    // - "Show launch trajectory from Pyongyang to Tokyo"
    // - "Visualize trajectory from Tehran to Tel Aviv"
    // ============================================================
    validateTrajectory: function(lower) {
        const self = this;
        const verbMatch = self.validVerbs.find(v => lower.startsWith(v))
            || (lower.startsWith('visualize') ? 'visualize' : null)
            || (lower.startsWith('plot') ? 'plot' : null);

        const typeMatch = self.validTrajectoryTypes.find(t => lower.includes(t));

        // Expect "from <origin> to <destination>"
        let fromMatch = null;
        let toMatch = null;
        let origin = null;
        let destination = null;

        if (typeMatch) {
            const typeEnd = lower.indexOf(typeMatch) + typeMatch.length;
            const afterType = lower.substring(typeEnd);
            const fromRegex = /\bfrom\b\s*(.*)/;
            const fromRegexMatch = afterType.match(fromRegex);
            if (fromRegexMatch) {
                fromMatch = 'from';
                const afterFrom = (fromRegexMatch[1] || '');

                // Progressive: allow just "from ..." without destination yet
                for (const tp of self.validTrajectoryToPreps) {
                    const tpWithSpaces = ' ' + tp + ' ';
                    const tpIdx = afterFrom.indexOf(tpWithSpaces);
                    const afterFromTrimmed = afterFrom.trimEnd();
                    const tpAtEnd = ' ' + tp;
                    const endsWithPrep = afterFromTrimmed.endsWith(tpAtEnd);
                    const tpEndIdx = endsWithPrep ? afterFromTrimmed.lastIndexOf(tpAtEnd) : -1;

                    if (tpIdx >= 0) {
                        toMatch = tp;
                        origin = afterFrom.substring(0, tpIdx).trim();
                        destination = afterFrom.substring(tpIdx + tp.length + 2).trim().replace(/\.$/, '');
                        break;
                    } else if (tpEndIdx >= 0) {
                        toMatch = tp;
                        origin = afterFromTrimmed.substring(0, tpEndIdx).trim();
                        destination = '';
                        break;
                    }
                }

                if (!toMatch && afterFrom.trim()) {
                    origin = afterFrom.replace(/\.$/, '').trim();
                }
            }
        }

        // Origin/destination can be country or city; we reuse those lists for exact/fuzzy
        const locationOptions = [...self.validCountries, ...self.validCities];
        let originStatus = false;
        let destinationStatus = destination ? false : null;
        let originMatch = null;
        let destinationMatch = null;

        if (origin) {
            const originLower = origin.toLowerCase();
            if (locationOptions.includes(originLower)) {
                originStatus = 'exact';
                originMatch = originLower;
            } else {
                originMatch = self.fuzzyMatch(origin, locationOptions);
                if (originMatch) originStatus = 'fuzzy';
            }
        }

        if (destination) {
            const destLower = destination.toLowerCase();
            if (locationOptions.includes(destLower)) {
                destinationStatus = 'exact';
                destinationMatch = destLower;
            } else {
                destinationMatch = self.fuzzyMatch(destination, locationOptions);
                if (destinationMatch) destinationStatus = 'fuzzy';
            }
        }

        const allExact = !!verbMatch && !!typeMatch && !!fromMatch && (originStatus === 'exact') && !!toMatch && (destinationStatus === 'exact');
        const allValid = !!verbMatch && !!typeMatch && !!fromMatch && !!originMatch && !!toMatch && !!destinationMatch;
        const hasFuzzy = originStatus === 'fuzzy' || destinationStatus === 'fuzzy';
        const partialValid = !!typeMatch || !!originMatch || !!destinationMatch;

        return {
            allExact, allValid, hasFuzzy, partialValid, toolName: 'Launch Trajectory',
            verbMatch, typeMatch, fromMatch, toMatch,
            origin, destination,
            originStatus, destinationStatus,
            originMatch, destinationMatch
        };
    },
    
    // ============================================================
    // Detect command type from input
    // ============================================================
    detectCommandType: function(lower) {
        const hasReverse = lower.includes('reverse') || lower.includes('launch envelope');
        const hasMinimum = lower.includes('minimum') || lower.includes('min distance') || lower.includes('minimum distance');
        const hasMultiple = lower.includes('multiple');
        const hasSingle = (lower.includes('single') || lower.includes('range ring')) && !hasReverse && !hasMinimum && !hasMultiple;
        const hasCustomPoi = lower.includes('poi') || lower.includes('point of interest') || lower.includes('custom poi');
        const hasTrajectory = lower.includes('trajectory') || lower.includes('flight path') || lower.includes('launch path');
        const hasVerb = /^(generate|create|build|show|calculate|compute)/i.test(lower);
        return { hasReverse, hasSingle, hasMinimum, hasMultiple, hasCustomPoi, hasTrajectory, hasVerb };
    },

    // ============================================================
    // Validate Custom POI command (lightweight syntactic check)
    // ============================================================
    validateCustomPoi: function(lower) {
        const self = this;
        const typeMatch = self.validCustomPoiTypes.find(t => lower.includes(t));

        // Strip leading label like "custom poi(s):" before splitting
        const cleaned = lower.replace(/^\s*custom\s+poi[s]?:\s*/, '');
        // Split groups by semicolon/newline/brackets
        const groups = cleaned.split(/;|\n|\]\s*\[|\[|\]/).map(g => g.trim()).filter(Boolean);
        const poiResults = [];
        let anyError = false;
        let anyFuzzy = false;
        let poiCount = 0;

        groups.forEach((g, idx) => {
            // Try to capture name (optional) + lat lon + range(s) + unit
            const regex = /([a-zA-Z\s']+)?\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?)?\s*(km|mi)?/;
            const m = g.match(regex);
            if (!m) {
                // Allow partial lat/lon pairs without ranges to stay fuzzy instead of error so we don't discard other POIs
                const fallback = g.match(/([a-zA-Z\s']+)?\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)/);
                if (fallback) {
                    const name = (fallback[1] || `POI ${idx + 1}`).trim();
                    const lat = parseFloat(fallback[2]);
                    const lon = parseFloat(fallback[3]);
                    poiResults.push({
                        status: 'error',
                        message: `POI ${idx + 1}: range required (max or min-max)`,
                        name,
                        lat,
                        lon,
                        minRange: null,
                        maxRange: null,
                        unit: null,
                    });
                    anyError = true;
                    return;
                }
                poiResults.push({ status: 'error', message: `POI ${idx + 1}: could not parse lat/lon/range`, raw: g });
                anyError = true;
                return;
            }

            const name = (m[1] || `POI ${idx + 1}`).trim();
            const lat = parseFloat(m[2]);
            const lon = parseFloat(m[3]);
            const r1 = m[4] ? parseFloat(m[4]) : null;
            const r2 = m[5] ? parseFloat(m[5]) : null;
            const unit = m[6] ? m[6].toLowerCase() : null;

            let minRange = 0;
            let maxRange = null;
            if (r1 !== null && r2 !== null) {
                minRange = r1;
                maxRange = r2;
            } else if (r1 !== null) {
                minRange = 0;
                maxRange = r1;
            }

            let status = 'exact';
            const msgs = [];

            if (maxRange === null || isNaN(maxRange)) {
                status = 'error';
                msgs.push('range required (max or min-max)');
            }
            if (!(unit && self.validCustomPoiUnits.includes(unit))) {
                status = 'error';
                msgs.push('unit required (km or mi)');
            }
            if (maxRange === null || isNaN(maxRange) || maxRange <= 0) {
                status = 'error';
                msgs.push('max range must be > 0');
            }
            if (minRange < 0) {
                status = 'error';
                msgs.push('min range cannot be negative');
            }
            if (minRange > 0 && maxRange !== null && maxRange <= minRange) {
                status = 'error';
                msgs.push('max range must exceed min range');
            }
            if (lat < -90 || lat > 90) {
                status = 'error';
                msgs.push('lat must be between -90 and 90');
            }
            if (lon < -180 || lon > 180) {
                status = 'error';
                msgs.push('lon must be between -180 and 180');
            }
            if (maxRange !== null && maxRange > 20000 && status !== 'error') {
                status = 'fuzzy';
                msgs.push('max range very large; verify');
            }

            if (status === 'fuzzy') anyFuzzy = true;
            if (status === 'error') anyError = true;

            poiCount += 1;
            poiResults.push({ status, name, lat, lon, minRange, maxRange, unit, messages: msgs });
        });

        const allExact = !anyError && !anyFuzzy && poiResults.length > 0 && !!typeMatch;
        const allValid = !anyError && poiResults.length > 0 && !!typeMatch;
        const hasFuzzy = anyFuzzy;
        const partialValid = typeMatch || poiResults.length > 0;

        const mode = poiCount > 1 ? 'Multiple' : 'Single';

        return { allExact, allValid, hasFuzzy, partialValid, toolName: 'Custom POI', poiResults, typeMatch, mode, poiCount };
    },
    
    // ============================================================
    // Set status for validator field (helper for validators)
    // ============================================================
    setFieldStatus: function(id, valid, value, matched, prefix) {
        prefix = prefix || '';
        const icon = document.getElementById(prefix + id + '-icon');
        const valueEl = document.getElementById(prefix + id + '-value');
        if (!icon || !valueEl) return;
        
        if (valid === 'exact') {
            icon.textContent = '✓';
            icon.className = prefix + 'icon ' + prefix + 'valid';
        } else if (valid === 'fuzzy') {
            icon.textContent = '⚠';
            icon.className = prefix + 'icon ' + prefix + 'warning';
        } else if (valid === false) {
            icon.textContent = '✗';
            icon.className = prefix + 'icon ' + prefix + 'invalid';
        } else {
            icon.textContent = '○';
            icon.className = prefix + 'icon ' + prefix + 'pending';
        }
        
        if (value && matched && matched !== value.toLowerCase()) {
            valueEl.innerHTML = value + '<span class="' + prefix + 'match"> (use: ' + matched + ')</span>';
        } else {
            valueEl.textContent = value || '—';
        }
    },
    
    // ============================================================
    // Setup lookup search box (helper for validators)
    // ============================================================
    setupLookup: function(inputId, suggestionsId, displayOptions, suggestionClass) {
        const self = this;
        const input = document.getElementById(inputId);
        const suggestions = document.getElementById(suggestionsId);
        if (!input || !suggestions) return;
        
        input.addEventListener('input', function() {
            const val = this.value;
            const matches = self.getFuzzyMatches(val, displayOptions, 10);
            
            if (matches.length > 0) {
                suggestions.innerHTML = matches.map(m => 
                    '<div class="' + suggestionClass + '">' + m + '</div>'
                ).join('');
                suggestions.classList.add('active');
            } else {
                suggestions.innerHTML = '<div class="' + suggestionClass.replace('suggestion', 'no-results') + '">No matches found</div>';
                suggestions.classList.add('active');
            }
        });
        
        input.addEventListener('focus', function() {
            if (this.value.length >= 1 || suggestions.innerHTML) {
                suggestions.classList.add('active');
            }
        });
        
        input.addEventListener('blur', function() {
            setTimeout(() => suggestions.classList.remove('active'), 200);
        });
        
        suggestions.addEventListener('click', function(e) {
            if (e.target.classList.contains(suggestionClass)) {
                input.value = e.target.textContent;
                suggestions.classList.remove('active');
            }
        });
    },
    
    // ============================================================
    // Attach listener to textarea (helper for all widgets)
    // ============================================================
    attachTextareaListener: function(callback) {
        const textareas = window.parent.document.querySelectorAll('textarea');
        for (const ta of textareas) {
            if (ta.placeholder && ta.placeholder.includes('Type a question')) {
                ta.addEventListener('input', function(e) {
                    callback(e.target.value);
                });
                callback(ta.value);
                return true;
            }
        }
        return false;
    }
};
