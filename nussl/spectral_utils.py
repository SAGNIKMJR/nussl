#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
import scipy.fftpack as scifft
import scipy.signal
import os.path
import librosa
import json
import warnings

import constants


def plot_stft(signal, file_name, title=None, win_length=None, hop_length=None,
              window_type=None, sample_rate=None, n_fft_bins=None,
              freq_max=None, show_interactive_plot=False, use_librosa=constants.USE_LIBROSA_STFT):
    """
    Outputs an image of an stft plot of input audio, signal. This uses matplotlib to create the output file.
    You can specify the same all of the same parameters that are in e_stft(). By default, the StftParams defaults
    are used for any values not provided in (win_length, hop_length, and window_type).
    Title is settable by user and there is a flag to show an interactive matplotlib graph, as well.

    Notes:
        To find out what output formats are available for your machine run the following code:
        ::
        import matplotlib.pyplot as plt
        fig = plt.figure()

        print fig.canvas.get_supported_filetypes()

        (From here: http://stackoverflow.com/a/7608273/5768001)

    Args:
        signal: (np.array) input time series signal that will be plotted
        file_name: (str) path to file that will be output. Will overwrite any file that is already there.
        Uses mat
        title: (string) (Optional) Title to go at top of graph. Defaults to 'Spectrogram of [file_name]'
        win_length: (int) (Optional) number of samples per window. Defaults to StftParams default.
        hop_length: (int) (Optional) number of samples between the start of adjacent windows, or "hop".
        Defaults to StftParams default.
        sample_rate: (int) (Optional) sample rate of input signal.  Defaults to StftParams default.
        window_type: (string) (Optional) type of window to use. Using WindowType object is recommended.
        Defaults to StftParams default.
        n_fft_bins: (int) (Optional) number of fft bins per time window.
        If not specified, defaults to next highest power of 2 above window_length. Defaults to StftParams default.
        freq_max: (int) Max frequency to display. Defaults to 44100Hz
        show_interactive_plot: (bool) (Optional) Flag indicating if plot should be shown when function is run.
        Defaults to False

    Examples:
    ::
    # Set up sine wave parameters
    sr = nussl.Constants.DEFAULT_SAMPLE_RATE # 44.1kHz
    n_sec = 3 # seconds
    duration = n_sec * sr
    freq = 300 # Hz

    # Make sine wave array
    x = np.linspace(0, freq * 2 * np.pi, duration)
    x = np.sin(x)

    # plot it and save it in path 'path/to/sine_wav.png'
    nussl.plot_stft(x, 'path/to/sine_wav.png')

    """
    sample_rate = constants.DEFAULT_SAMPLE_RATE if sample_rate is None else sample_rate
    freq_max = constants.MAX_FREQUENCY if freq_max is None else freq_max

    if title is None:
        title = os.path.basename(file_name)
        title = os.path.splitext(title)[0]
        title = 'Spectrogram of {}'.format(title)

    required = [win_length, hop_length, window_type]
    if any([r is None for r in required]):
        defaults = StftParams(sample_rate)

        win_length = defaults.window_length if win_length is None else win_length
        hop_length = defaults.hop_length if hop_length is None else hop_length
        window_type = defaults.window_type if window_type is None else window_type

    (stft, psd, freqs, time) = e_stft_plus(signal, win_length, hop_length,
                                           window_type, sample_rate, n_fft_bins,
                                           use_librosa)

    plt.close('all')

    # TODO: remove transposes!
    time_tile = np.tile(time, (len(freqs), 1))
    freq_tile = np.tile(freqs.T, (len(time), 1)).T
    sp = librosa.logamplitude(np.abs(stft) ** 2, ref_power=np.max)
    plt.pcolormesh(time_tile, freq_tile, sp)

    plt.axis('tight')
    plt.xlabel('Time (sec)')
    plt.ylabel('Frequency (Hz)')
    plt.title(title)
    plt.ylim(freqs[0], freq_max)

    plt.savefig(file_name)

    if show_interactive_plot:
        plt.interactive('True')
        plt.show()


def e_stft(signal, window_length, hop_length, window_type,
           n_fft_bins=None, remove_reflection=True, remove_padding=False):
    """
    This function computes a short time fourier transform (STFT) of a 1D numpy array input signal.
    This will zero pad the signal by half a hop_length at the beginning to reduce the window
    tapering effect from the first window. It also will zero pad at the end to get an integer number of hops.

    By default, this function removes the FFT data that is a reflection from over Nyquist. There is an option
    to suppress this behavior and have this function include data from above Nyquist, but since the
    inverse STFT function, e_istft(), expects data without the reflection, the onus is on the user to remember
    to set the reconstruct_reflection flag in e_istft() input.

    Additionally, this function assumes a single channeled audio signal and is not guaranteed to work on
    multichannel audio. If you want to do an STFT on multichannel audio see the AudioSignal object.

    Args:
        signal: 1D numpy array containing audio data. (REAL?COMPLEX?INTEGER?)
        window_length: (int) number of samples per window
        hop_length: (int) number of samples between the start of adjacent windows, or "hop"
        window_type: (string) type of window to use. Using WindowType object is recommended.
        n_fft_bins: (int) (Optional) number of fft bins per time window.
        If not specified, defaults to next highest power of 2 above window_length
        remove_reflection: (bool) (Optional) if True, this will remove reflected STFT data above the Nyquist point.
        If not specified, defaults to True.
        remove_padding: (bool) (Optional) if True, this will remove the extra padding added when doing the STFT.
        Defaults to True.

    Returns:
        2D  numpy array with complex STFT data.
        Data is of shape (num_time_blocks, num_fft_bins). These numbers are determined by length of the input signal,
        on internal zero padding (explained at top), and n_fft_bins/remove_reflection input (see example below).

    Examples:
        ::
        # Set up sine wave parameters
        sr = nussl.Constants.DEFAULT_SAMPLE_RATE # 44.1kHz
        n_sec = 3 # seconds
        duration = n_sec * sr
        freq = 300 # Hz

        # Make sine wave array
        x = np.linspace(0, freq * 2 * np.pi, duration)
        x = np.sin(x)

        # Set up e_stft() parameters
        win_type = nussl.WindowType.HANN
        win_length = 2048
        hop_length = win_length / 2

        # Run e_stft()
        stft = nussl.e_stft(x, win_length, hop_length, win_type)
        # stft has shape (win_length // 2 + 1 , duration / hop_length)

        # Get reflection
        stft_with_reflection = nussl.e_stft(x, win_length, hop_length, win_type, remove_reflection=False)
        # stft_with_reflection has shape (win_length, duration / hop_length)

        # Change number of fft bins per hop
        num_bins = 4096
        stft_more_bins = e_stft(x, win_length, hop_length, win_type, n_fft_bins=num_bins)
        # stft_more_bins has shape (num_bins // 2 + 1, duration / hop_length)
    """
    if n_fft_bins is None:
        n_fft_bins = int(2 ** np.ceil(np.log2(window_length)))

    window_type = constants.WINDOW_DEFAULT if window_type is None else window_type
    window = make_window(window_type, window_length)

    signal, zero_pad1, zero_pad2 = _add_zero_padding(signal, window_length, hop_length)

    # figure out size of output stft
    num_blocks = int(((len(signal) - window_length) / hop_length + 1))
    stft_bins = n_fft_bins // 2 + 1 if remove_reflection else n_fft_bins  # only want just over half of each fft

    # this is where we do the stft calculation
    stft = np.zeros((num_blocks, stft_bins), dtype=complex)
    for hop in range(num_blocks):
        start = hop * hop_length
        end = start + window_length
        unwindowed_signal = signal[start:end]
        windowed_signal = np.multiply(unwindowed_signal, window)
        fft = scifft.fft(windowed_signal, n=n_fft_bins)
        stft[hop, ] = fft[0:stft_bins]

    # reshape the 2d array, so it's how we expect it.
    stft = stft.T
    stft = _remove_stft_padding(stft, zero_pad1, zero_pad2, hop_length) if remove_padding else stft

    return stft


def librosa_stft_wrapper(signal, window_length, hop_length, window_type=None, remove_reflection=True,
                         remove_padding=True, center=True, n_fft_bins=None):
    """

    Args:
        signal:
        window_length:
        hop_length:
        window_type:
        remove_reflection:
        remove_padding:
        center:
        n_fft_bins:

    Returns:

    """

    if window_type is not None and n_fft_bins is not None:
        warnings.warn('n_fft_bins ignored. Librosa\'s stft uses window_length as n_fft_bins')

    signal, zero_pad1, zero_pad2 = _add_zero_padding(signal, window_length, hop_length)

    window = make_window(window_type, window_length) if window_type is not None else None

    stft = librosa.stft(signal, n_fft=window_length, hop_length=hop_length, win_length=window_length,
                        window=window, center=center)

    stft = stft if remove_reflection else _add_reflection(stft)

    stft = _remove_stft_padding(stft, zero_pad1, zero_pad2, hop_length) if remove_padding else stft

    return stft


def e_istft(stft, window_length, hop_length, window_type, reconstruct_reflection=True, remove_padding=False):
    """
    Computes an inverse short time fourier transform (STFT) from a 2D numpy array of complex values. By default
    this function assumes input STFT has no reflection above Nyquist and will rebuild it, but the
    reconstruct_reflection flag overrides that behavior.

    Additionally, this function assumes a single channeled audio signal and is not guaranteed to work on
    multichannel audio. If you want to do an iSTFT on multichannel audio see the AudioSignal object.

    Args:
        stft: complex valued 2D numpy array containing STFT data
        window_length: (int) number of samples per window
        hop_length: (int) number of samples between the start of adjacent windows, or "hop"
        window_type: (deprecated)
        reconstruct_reflection: (bool) (Optional) if True, this will recreate the removed reflection
        data above the Nyquist. If False, this assumes that the input STFT is complete. Default is True.
        remove_padding: (bool) (Optional) if True, this function will remove the first and
            last (window_length - hop_length) number of samples. Defaults to False.
        will massage the output so that it is in a format that it expects. remove_reflection is still works in this
        mode. Note: librosa's works differently than nussl's and may produce different output.

    Returns:
        1D numpy array containing an audio signal representing the original signal used to make stft

    Examples:
        ::
        # Set up sine wave parameters
        sr = nussl.Constants.DEFAULT_SAMPLE_RATE # 44.1kHz
        n_sec = 3 # seconds
        duration = n_sec * sr
        freq = 300 # Hz

        # Make sine wave array
        x = np.linspace(0, freq * 2 * np.pi, duration)
        x = np.sin(x)

        # Set up e_stft() parameters
        win_type = nussl.WindowType.HANN
        win_length = 2048
        hop_length = win_length / 2

        # Get an stft
        stft = nussl.e_stft(x, win_length, hop_length, win_type)

        calculated_signal = nussl.e_istft(stft, win_length, hop_length)
    """

    n_hops = stft.shape[1]
    signal_length = ((n_hops - 1) * hop_length) - window_length # ?
    signal_length = (n_hops - 1) * hop_length + window_length
    signal = np.zeros(signal_length)

    # Add reflection back
    if reconstruct_reflection:
        stft = _add_reflection(stft)

    for n in range(n_hops):
        start = n * hop_length
        end = start + window_length
        signal[start:end] = signal[start:end] + np.real(scifft.ifft(stft[:, n]))

    # remove zero-padding
    if remove_padding:
        start = window_length - hop_length
        stop = signal_length - (window_length - hop_length)
        signal = signal[start:stop]

    return signal


def librosa_istft_wrapper(stft, window_length, hop_length, window_type,
                          remove_reflection=False, remove_padding=False, center=True):
    """

    Args:
        stft:
        window_length:
        hop_length:
        window_type:
        remove_reflection:
        remove_padding:

    Returns:

    """
    window = get_window_function(window_type) if window_type is not None else None

    if remove_reflection:
        n_fft = stft.shape[0]
        n_fft -= 1 if n_fft % 2 == 0 else 0
        stft = stft[:n_fft, :]

    signal = librosa.istft(stft, hop_length, window_length, window, center)

    # remove zero-padding
    if remove_padding:
        start = window_length - hop_length
        n_hops = stft.shape[1]
        signal_length = (n_hops - 1) * hop_length + window_length
        stop = signal_length - (window_length - hop_length)
        signal = signal[start:stop]

    return signal


def e_stft_plus(signal, window_length, hop_length, window_type, sample_rate,
                n_fft_bins=None, remove_reflection=True, use_librosa=constants.USE_LIBROSA_STFT):
    """
    Does a short time fourier transform (STFT) of the signal (by calling e_stft() ), but also calculates
    the power spectral density (PSD), frequency and time vectors for the calculated STFT. This function does not
    give you as many options as e_stft() (wrt removing the reflection and using librosa). If you need that
    flexibility, it is recommended that you either use e_stft() or use an AudioSignal object.

    Use this is situations where you need more than just the STFT data. For instance, this is used in plot_stft()
    to get the frequency vector to graph. In situations where you don't need this extra data it is
    more efficient to use e_stft().

    Additionally, this function assumes a single channeled audio signal and is not guaranteed to work on
    multichannel audio. If you want to do an STFT on multichannel audio see the AudioSignal object.

    Args:
        signal: 1D numpy array containing audio data. (REAL?COMPLEX?INTEGER?)
        window_length: (int) number of samples per window
        hop_length: (int) number of samples between the start of adjacent windows, or "hop"
        window_type: (string) type of window to use. Using WindowType object is recommended.
        sample_rate: (int) the intended sample rate, this is used in the calculation of the frequency vector
        n_fft_bins: (int) (Optional) number of fft bins per time window.
        If not specified, defaults to next highest power of 2 above window_length

    Returns:
        stft: (np.ndarray) a 2D matrix short time fourier transform data

    """

    if n_fft_bins is None:
        n_fft_bins = window_length

    stft = e_stft(signal, window_length, hop_length, window_type, n_fft_bins, remove_reflection, use_librosa)

    if use_librosa or remove_reflection:
        frequency_vector = (sample_rate / 2) * np.linspace(0, 1, (n_fft_bins / 2) + 1)
    else:
        frequency_vector = sample_rate * np.linspace(0, 1, n_fft_bins + 1)

    time_vector = np.array(range(stft.shape[1]))
    hop_in_secs = hop_length / (1.0 * sample_rate)
    time_vector = np.multiply(hop_in_secs, time_vector)

    window_type = constants.WINDOW_DEFAULT if window_type is None else window_type
    window = make_window(window_type, window_length)
    win_dot = np.dot(window, window.T)
    psd = np.zeros_like(stft, dtype=float)
    for i in range(psd.shape[1]):
        psd[:, i] = (1 / float(sample_rate)) * ((abs(stft[:, i]) ** 2) / float(win_dot))

    return stft, psd, frequency_vector, time_vector


def _add_zero_padding(signal, window_length, hop_length):
    """

    Args:
        signal:
        window_length:
        hop_length:

    Returns:

    """
    orig_signal_length = len(signal)

    # zero-pad the vector at the beginning and end to reduce the window tapering effect
    window_length -= 1 if window_length % 2 != 0 else 0 # subtract 1 if window_length is an odd number
    zero_pad1_len = window_length // 2
    signal = np.lib.pad(signal, (zero_pad1_len, zero_pad1_len), 'constant', constant_values=(0, 0))

    # another zero pad at the end if not integer multiple of hop_length
    zero_pad2_len = 0
    if orig_signal_length % hop_length != 0:
        zero_pad2_len = hop_length - (orig_signal_length % hop_length)
        signal = np.lib.pad(signal, (0, zero_pad2_len), 'constant', constant_values=(0, 0))

    return signal, zero_pad1_len, zero_pad2_len


def _remove_stft_padding(stft, zero_pad1_len, zero_pad2_len, hop_length):
    """

    Args:
        stft:
        zero_pad1_len:
        zero_pad2_len:
        hop_length:

    Returns:

    """
    first = zero_pad1_len // hop_length
    last = stft.shape[1] - (zero_pad1_len + zero_pad2_len) // hop_length
    stft = stft[:, first: last]
    return stft


def make_window(window_type, length):
    """Returns an np array of type window_type

    Args:
        window_type (basestring): Type of window to create, string can be
        length (int): length of window

    Returns:
        window (np.array): np array with a window of type window_type
    """

    # Generate samples of a normalized window
    if window_type == constants.WINDOW_RECTANGULAR:
        return np.ones(length)
    elif window_type == constants.WINDOW_HANN:
        return scipy.signal.hann(length, False)
    elif window_type == constants.WINDOW_BLACKMAN:
        return scipy.signal.blackman(length, False)
    elif window_type == constants.WINDOW_HAMMING:
        return scipy.signal.hamming(length, False)
    else:
        return None


def get_window_function(window_type):
    """
    Gets a window function from scipy.signal
    Args:
        window_type: (string) name of the window function from scipy.signal

    Returns: callable window function from scipy.signal

    """
    return getattr(scipy.signal, window_type)

def _add_reflection(matrix):
    reflection = matrix[-2:0:-1, :]
    reflection = reflection.conj()
    return np.vstack((matrix, reflection))


class StftParams(object):
    """
    The StftParams class is a container for information needed to run an STFT or iSTFT.
    This is meant as a convenience and does not actually perform any calculations within. It should
    get "decomposed" by the time e_stft() or e_istft() are called, so that every attribute in this
    object is a parameter to one of those functions.

    Every class that inherits from the SeparationBase class has an StftParms object, and this
    is the only way that a top level user has access to the STFT parameter settings that
    all of the separation algorithms are built upon.
    This object will get passed around instead of each of these individual attributes.
    """
    def __init__(self, sample_rate, window_length=None, hop_length=None, window_type=None, n_fft_bins=None):
        self.sample_rate = sample_rate

        # default to 40ms windows
        default_win_len = int(2 ** (np.ceil(np.log2(constants.DEFAULT_WIN_LEN_PARAM * sample_rate))))
        self._window_length = default_win_len if window_length is None else window_length
        self._hop_length = self._window_length / 2 if hop_length is None else hop_length
        self.window_type = constants.WINDOW_DEFAULT if window_type is None else window_type
        self._n_fft_bins = self._window_length if n_fft_bins is None else n_fft_bins

        self._hop_length_needs_update = True
        self._n_fft_bins_needs_update = True

        if hop_length is not None:
            self._hop_length_needs_update = False

        if n_fft_bins is not None:
            self._n_fft_bins_needs_update = False

    @property
    def window_length(self):
        return self._window_length

    @window_length.setter
    def window_length(self, value):
        """
        Length of stft window in samples. If window_overlap
        or num_fft are not set manually, then changing this will update them to
        hop_length = window_length // 2, and and num_fft = window_length
        This property is settable.
        """
        self._window_length = value

        if self._n_fft_bins_needs_update:
            self._n_fft_bins = value

        if self._hop_length_needs_update:
            self._hop_length = value // 2

    @property
    def hop_length(self):
        return self._hop_length

    @hop_length.setter
    def hop_length(self, value):
        """
        Number of samples that e_stft will jump ahead for every time slice.
        By default, this is equal to half of self.window_length and will update when you
        change self.window_length to stay at self.window_length // 2. If you set self.hop_length directly
        then self.hop_length and self.window_length are unlinked.
        This property is settable.
        """
        self._hop_length_needs_update = False
        self._hop_length = value

    @property
    def n_fft_bins(self):
        """

        Returns:

        """
        return self._n_fft_bins

    @n_fft_bins.setter
    def n_fft_bins(self, value):
        """
        Number of fft bins per time slice in the stft. A time slice is of length window length.
        By default the number of FFT bins is equal to window_length (value of window_length),
        but if this is set manually then e_stft takes a window of length.
        If you give it a value lower than self.window_length, self.window_length will be used.
        This property is settable.

        """
        # TODO: add warning for this
        if value < self.window_length:
            value = self.window_length

        self._n_fft_bins_needs_update = False
        self._n_fft_bins = value

    @property
    def window_overlap(self):
        """
        Returns number of samples of overlap between adjacent time slices.
        This is calculated like self.window_length - self.hop_length
        This property is not settable.
        """
        return self.window_length - self.hop_length

    def to_json(self):
        return json.dumps(self, default=self._to_json_helper)

    def _to_json_helper(self, o):
        if not isinstance(o, StftParams):
            raise TypeError
        d = {'__class__': o.__class__.__name__,
             '__module__': o.__module__}
        d.update(o.__dict__)
        return d

    @staticmethod
    def from_json(json_string):
        return json.loads(json_string, object_hook=StftParams._from_json_helper)

    @staticmethod
    def _from_json_helper(json_dict):
        if '__class__' in json_dict:
            class_name = json_dict.pop('__class__')
            module = json_dict.pop('__module__')
            if class_name != StftParams.__name__ or module != StftParams.__module__:
                raise TypeError
            sr = json_dict['sample_rate']
            s = StftParams(sr)
            for k, v in json_dict.items():
                s.__dict__[k] = v if not isinstance(v, unicode) else v.encode('ascii')
            return s
        else:
            return json_dict

    def __eq__(self, other):
        return all([v == other.__dict__[k] for k, v in self.__dict__.items()])

    def __ne__(self, other):
        return not self == other
