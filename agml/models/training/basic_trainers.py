# Copyright 2021 UC Davis Plant AI and Biophysics Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import datetime

from pytorch_lightning import Trainer
from pytorch_lightning.loggers import TensorBoardLogger, Logger
from pytorch_lightning.callbacks import ModelCheckpoint

from agml.models.classification import ClassificationModel
from agml.models.system_utils import get_accelerator
from agml.utils.logging import log


def train_classification(model,
                         *,
                         dataset=None,
                         epochs=50,
                         loss=None,
                         metrics=None,
                         optimizer=None,
                         lr_scheduler=None,
                         lr=None,
                         loggers=None,
                         train_dataloader=None,
                         val_dataloader=None,
                         test_dataloader=None,
                         use_cpu=False,
                         save_dir=None,
                         experiment_name=None,
                         **kwargs):
    """Trains an image classification model.

    This method can be used to train an image classification model on a given
    dataset (which should be an `AgMLDataLoader`. Alternatively, if you already
    have separate dataloaders for training, validation, and testing, you can
    pass them in as keyword arguments). This method will train the model for
    the given number of epochs, and then return the trained model.

    You can take advantage of keyword arguments to provide additional training
    parameters, e.g., a custom optimizer or optimizer name. If nothing is provided
    for these parameters (see below for an extended list), then defaults are used.

    This method provides a simple interface for training models, but it is not
    a fully-flexible or customizable training loop. If you need more control over
    the training loop, then you should manually define your arguments. Furthermore,
    if you need custom control over the training loop, then you should reimplement
    the training/validation/test loops on your own in the original model class.

    Parameters
    ----------
    model : AgMLModelBase
        The model to train.
    dataset : AgMLDataLoader
        The name of the dataset to use for training. This should be an AgMLDataLoader
        with the data split in the intended splits, and all preprocessing/transforms
        already applied to the loader. This method will automatically figure out the
        splits from the dataloader.
    epochs : int
        The number of epochs to train for.
    loss : {str, torch.nn.Module}
        The loss function to use for training. If none is provided, then the default
        loss function is used (cross-entropy loss).
    metrics : {str, List[str]}
        The metrics to use for training. If none are provided, then the default
        metrics are used (accuracy).
    optimizer : torch.optim.Optimizer
        The optimizer to use for training. If none is provided, then the default
        optimizer is used (Adam).
    lr_scheduler : torch.optim.lr_scheduler._LRScheduler
        The learning rate scheduler to use for training. If none is provided, then
        no learning rate scheduler is used.
    lr : float
        The learning rate to use for training. If none is provided, then the default
        learning rate is used (1e-3).
    loggers : Any
        The loggers to use for training. If none are provided, then the default
        loggers are used (TensorBoard)

    train_dataloader : torch.utils.data.DataLoader
        The dataloader to use for training. If none is provided, then the dataloader
        is loaded from the dataset.
    val_dataloader : torch.utils.data.DataLoader
        The dataloader to use for validation. If none is provided, then the dataloader
        is loaded from the dataset.
    test_dataloader : torch.utils.data.DataLoader
        The dataloader to use for testing. If none is provided, then the dataloader
        is loaded from the dataset.

    use_cpu : bool
        If True, then the model will be trained on the CPU, even if a GPU is available.
        This is useful for debugging purposes (or if you are on a Mac, where MPS
        acceleration may be buggy).
    save_dir : str
        The directory to save the model and any logs to. If none is provided, then
        the model is saved to the current working directory in a folder which is
        called `agml_training_logs`.
    experiment_name : str
        The name of the experiment. If none is provided, then the experiment name
        is set to a custom format (the task + the dataset + the current date).

    Returns
    -------
    AgMLModelBase
        The trained model with the best loaded weights. This model can be used for
        inference, or for further training.
    """

    # Run data checks:
    # (1) The input dataset is a valid image classification dataset
    # (2) The input dataset has split data
    # (3) Only one of `dataset` and the `dataloader`s has been passed.
    if not dataset.info.tasks.ml == 'image_classification':
        raise ValueError("The dataset must be an image classification dataset.")
    dataset_exists, dataloader_exists = \
        dataset is not None, any([train_dataloader, val_dataloader, test_dataloader])
    if dataset_exists ^ dataloader_exists:
        raise ValueError("You can only pass one of the dataset/dataloader arguments.")

    if dataset_exists:
        if not dataset._is_split:
            raise ValueError("The provided dataset must have split data.")
        if dataset.train_data is not None:
            train_dataloader = dataset.train_data
        if dataset.val_data is not None:
            val_dataloader = dataset.val_data
        if dataset.test_data is not None:
            test_dataloader = dataset.test_data
        dataset_name = dataset.info.name

    # Set up the model for training (and choose the default parameters).
    if not isinstance(model, ClassificationModel):
        raise ValueError("Expected an `agml.models.ClassificationModel` for an image "
                         "classification task, instead got {}.".format(type(model)))

    if loss is None:
        loss = 'ce'
    if optimizer is None:
        optimizer = 'adam'
    if metrics is None:
        metrics = ['accuracy']
    elif isinstance(metrics, str):
        metrics = [metrics]
    if lr is None:
        if kwargs.get('learning_rate', None) is not None:
            lr = kwargs['learning_rate']
        else:
            lr = 1e-3
    elif lr is not None and kwargs.get('learning_rate', None) is not None:
        raise ValueError("You cannot pass both `lr` and `learning_rate`.")

    model._prepare_for_training(
        loss = loss,
        metrics = metrics,
        optimizer = optimizer,
        lr_scheduler = lr_scheduler,
        lr = lr,
    )

    # Set up the trainer.
    if save_dir is not None:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            log("Created directory ({}) for saving training logs.".format(save_dir))
    else:
        save_dir = os.path.join(os.getcwd(), 'agml_training_logs')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
            log("Created directory ({}) for saving training logs.".format(save_dir))
    if experiment_name is None:
        curr_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        if dataset_exists:
            experiment_name = '{}_{}_{}'.format(
                model.info.tasks.ml, dataset_name, curr_datetime)  # noqa
        else:
            experiment_name = '{}_{}_{}'.format(
                model.info.tasks.ml, 'unknown', curr_datetime)
    if loggers is not None:
        for _logger in loggers:
            if not isinstance(_logger, Logger):
                raise ValueError("Expected a `pytorch_lightning.loggers.Logger` for a "
                                 "logger, instead got {}.".format(type(_logger)))
    else:
        loggers = [TensorBoardLogger(save_dir, name = experiment_name)]
    checkpoint_callback = ModelCheckpoint(save_dir, monitor='val_loss', mode='min', save_top_k=1)

    trainer = Trainer(
        max_epochs = epochs,
        devices = get_accelerator(use_cpu = use_cpu),
        logger = loggers,
        callbacks = [checkpoint_callback],
        log_every_n_steps = 2,
    )

    # Train and test the model.
    trainer.fit(
        model,
        train_dataloaders = train_dataloader,
        val_dataloaders = val_dataloader,
    )

    if test_dataloader is not None:
        trainer.test(dataloaders = test_dataloader)

    # Get the saved path for the best model.
    best_model_path = checkpoint_callback.best_model_path
    log("The best model was saved to: {}".format(best_model_path))

    return model




