from torch.utils.data import Dataset
from .. import AudioSignal, STFTParams

class BaseDataset(Dataset):
    def __init__(self, folder, sample_rate=None, transforms=None):
        """
        The BaseDataset class is the starting point for all dataset hooks
        in nussl. To subclass BaseDataset, you only have to implement two 
        functions:

        - get_items: a function that is passed the folder and generates a
          list of items that will be processed by the next function. The
          number of items in the list will dictate len(dataset). Must return
          a list.
        - process_item: this function processes a single item in the list
          generated by get_items. Must return a dictionary.

        After process_item is called, a set of Transforms can be applied to the 
        output of process_item. If no transforms are defined (``self.transforms = None``),
        then the output of process_item is returned by self[i]. For implemented
        Transforms, see nussl.datasets.transforms. For example, 
        PhaseSpectrumApproximation will add three new keys to the output dictionary
        of process_item:

        - mix_magnitude: the magnitude spectrogram of the mixture
        - source_magnitudes: the magnitude spectrogram of each source
        - ideal_binary_mask: the ideal binary mask for each source

        For examples of subclassing, see ``nussl.datasets.hooks``.
        
        Args:
            folder (str): location that should be processed to produce the list of files
            sample_rate (int, optional): Sample rate to use for each audio files. If
                audio file sample rate doesn't match, it will be resampled on the fly.
                If None, uses the default sample rate. Defaults to None.
            transforms (list, optional): List of transforms to apply to the output of
                ``self.process_item``. Defaults to None.
        
        Raises:
            DataSetException: Exceptions are raised if the output of the implemented
                functions by the subclass don't match the specification.
        """
        self.folder = folder
        self.sample_rate = sample_rate
        self.transforms = transforms
        self.items = self.get_items(self.folder)
        if not isinstance(self.items, list):
            raise DataSetException("Output of self.get_items must be a list!")

    def get_items(self, folder):
        """This function must be implemented by whatever class inherits BaseDataset.
        It should return a list of items in the given folder, each of which is 
        processed by process_items in some way to produce mixes, sources, class
        labels, etc.

        Args:
            folder - location that should be processed to produce the list of files.

        Returns:
            list: list of items that should be processed
        """
        raise NotImplementedError()

    def __len__(self):
        """
        Gets the length of the dataset (the number of items that will be processed).

        Returns:
            int: Length of the dataset (``len(self.items)``).
        """
        return len(self.items)

    def __getitem__(self, i):
        """
        Processes a single item in ``self.items`` using ``self.process_item``.
        The output of ``self.process_item`` is further passed through bunch of
        of transforms if they are defined in parallel. If you want to have
        a set of transforms that depend on each other, then you should compose them
        into a single transforms and then pass it into here. The output of each
        transform is added to an output dictionary which is returned by this
        function.
        
        Args:
            i (int): Index of the dataset to return. Indexes ``self.items``.

        Returns:
            dict: Dictionary with keys and values corresponding to the processed
                item after being put through the set of transforms (if any are
                defined).
        """
        output = {}
        processed_item = self.process_item(self.items[i])

        if not isinstance(processed_item, dict):
            raise DataSetException(
                "The output of process_item must be a dictionary!")

        output.update(processed_item)

        if self.transforms:
            for transform in self.transforms:
                transform_output = transform(processed_item)
                if not isinstance(transform_output, dict):
                    raise DataSetException(
                        "The output of every transform must be a dictionary!")
                output.update(transform_output)

        return output

    def process_item(self, item):
        """Each file returned by get_items is processed by this function. For example,
        if each file is a json file containing the paths to the mixture and sources, 
        then this function should parse the json file and load the mixture and sources
        and return them.

        Exact behavior of this functionality is determined by implementation by subclass.

        Args:
            item (object): the item that will be processed by this function. Input depends
                on implementation of ``self.get_items``.

        Returns:
            This should return a dictionary that gets processed by the transforms.
        """
        raise NotImplementedError()

    def _load_audio_file(self, path_to_audio_file, sample_rate=None):
        """
        Loads audio file at given path. Uses AudioSignal to load the audio data
        from disk.

        Args:
            path_to_audio_file: relative or absolute path to file to load
            sample_rate (int, optional): the sample rate at which to load
                the audio file. If None, self.sample_rate or the sample rate of 
                the actual file is used. Defaults to None.

        Returns:
            AudioSignal: loaded AudioSignal object of path_to_audio_file
        """
        sample_rate = sample_rate if sample_rate else self.sample_rate
        audio_signal = AudioSignal(
            path_to_audio_file, sample_rate=sample_rate)
        return audio_signal
    
    def _load_audio_from_array(self, audio_data, sample_rate=None):
        """
        Loads the audio data into an AudioSignal object with the appropriate 
        sample rate.
        
        Args:
            audio_data (np.ndarray): numpy array containing the samples containing
                the audio data.
            sample_rate (int): the sample rate at which to load the audio file. 
                 If None, self.sample_rate or the sample rate of the actual file is used. 
                 Defaults to None.
        
        Returns:
            AudioSignal: loaded AudioSignal object of audio_data
        """
        sample_rate = sample_rate if sample_rate else self.sample_rate
        audio_signal = AudioSignal(
            audio_data_array=audio_data, sample_rate=sample_rate
        )
        return audio_signal    

class DataSetException(Exception):
    """
    Exception class for errors when working with data sets in nussl.
    """
    pass
