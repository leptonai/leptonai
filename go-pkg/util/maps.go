package util

// ContainsStringsMap returns true if superSet contains all elements of subset.
func ContainsStringsMap(superSet, subset map[string]string) bool {
	if len(superSet) < len(subset) {
		return false
	}
	for ksub, vsub := range subset {
		v2, ok := superSet[ksub]
		if !ok || vsub != v2 {
			return false
		}
	}
	return true
}
