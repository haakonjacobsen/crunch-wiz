import math
import pywt
import numpy as np


def modmax(d):
    # compute signal modulus
    m = [0.0] * len(d)
    for i in range(len(d)):
        m[i] = math.fabs(d[i])

    # if value is larger than both neighbours , and strictly
    # larger than either , then it is a local maximum
    t = [0.0] * len(d)
    for i in range(len(d)):
        ll = m[i - 1] if i >= 1 else m[i]
        oo = m[i]
        rr = m[i + 1] if i < len(d) - 2 else m[i]
        if (ll <= oo and oo >= rr) and (ll < oo or oo > rr):
            # compute magnitude
            t[i] = math.sqrt(d[i] ** 2)
        else:
            t[i] = 0.0
    return t


def lhipa(d, signal_dur):
    # find max decomposition level
    w = pywt.Wavelet("sym16")
    maxlevel = pywt.dwt_max_level(len(d), filter_len=w.dec_len)
    # set high and low frequency band indeces
    hif, lof = 1, int(maxlevel / 2)
    print(hif)
    print(lof)

    # get detail coefficients of pupil diameter signal d
    cD_H = pywt.downcoef("d", d, "sym16", "per", level=hif)
    cD_L = pywt.downcoef("d", d, "sym16", "per", level=lof)

    # normalize by 1/ 2j
    cD_H[:] = [x / math.sqrt(2 ** hif) for x in cD_H]
    cD_L[:] = [x / math.sqrt(2 ** lof) for x in cD_L]

    # obtain the LH:HF ratio
    cD_LH = cD_L
    for i in range(len(cD_L)):
        cD_LH[i] = cD_L[i] / cD_H[((2 ** lof) // (2 ** hif)) * i]

    # detect modulus maxima , see Duchowski et al. [15]
    cD_LHm = modmax(cD_LH)

    # threshold using universal threshold λuniv = σˆ (2logn)
    # where σˆ is the standard deviation of the noise
    λuniv = np.std(cD_LHm) * math.sqrt(2.0 * np.log2(len(cD_LHm)))
    cD_LHt = pywt.threshold(cD_LHm, λuniv, mode="less")

    # get signal duration (in seconds)
    tt = signal_dur
    # compute LHIPA
    ctr = 0
    for i in range(len(cD_LHt)):
        if math.fabs(cD_LHt[i]) > 0:
            ctr += 1
    LHIPA = float(ctr) / tt

    return LHIPA


def compute_cognitive_load(initTime, endTime, lpup, rpup):
    """
    Preprocesses parameters from eyetracker handler and calls lhipa to calculate cognitive load

    :param initTime: list of timestamps for start time of each data point
    :type initTime: list

    :param endTime: list of timestamps for end time of each data point
    :type endTime: list

    :param lpup: list of values for left pupil
    :type lpup: list

    :param rpup: list of values for right pupil
    :type rpup: list'
    :return: Measure of cognitive load
    """
    assert len(lpup) == len(rpup)
    signal_dur = endTime[-1] - initTime[0]
    average_pupil_values = []
    for i in range(len(lpup)):
        if lpup == "NA":
            lpup[i] = rpup[i]
        elif rpup == "NA":
            rpup[i] == lpup[i]
        average_pupil_values.append((lpup[i] + rpup[i]) / 2)

    return lhipa(average_pupil_values, signal_dur)