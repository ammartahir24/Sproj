import numpy as np
import json
from _ import Critical_Path,Apply


def Greedy(budget, dep_graph, trans_table):
	CP = Critical_Path(dep_graph)
	SSIM = 1
	CPlength = CP.length()
	while(CPlength > budget):
		nTT = sort(extract(trans_table, CP))
		curr_transform = nTT[0]
		dep_graph = Apply(curr_transform)
		SSIM = SSIM_update(curr_transform.id, SSIM, curr_transform.SSIM)
		CP = Critical_Path(dep_graph)
		CPlength = CP.length()
	return dep_graph,SSIM