# -*- coding: utf-8 -*-

"""SubstraFL, Colorectal polyps, models: ResNet, AlexNet, ZFNet, Bionnica. Performance metrics
"""

!pip install substrafl
!pip install numpy pandas scikit-learn tensorflow torchvision

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix
from substrafl.nodes import TrainDataNode, TestDataNode, TrainNode, AggregationNode, OutputNode
from substrafl.schemas import Dataset, Objective
from substrafl.strategies import FedAvg
from substrafl.algorithms import TorchFLAlgorithm
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset

class ColorectalDataset(Dataset):
    def __init__(self, images, labels, transform=None):
        self.images = images
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        image = self.images[idx]
        label = self.labels[idx]

        if self.transform:
            image = self.transform(image)

        return image, label

def get_model(model_name):
    if model_name == "resnet":
        model = models.resnet18(pretrained=True)
        model.fc = nn.Linear(model.fc.in_features, 2)
    elif model_name == "alexnet":
        model = models.alexnet(pretrained=True)
        model.classifier[6] = nn.Linear(model.classifier[6].in_features, 2)
    elif model_name == "zfnet":
        model = models.resnet50(pretrained=True)
        model.fc = nn.Linear(model.fc.in_features, 2)
    elif model_name == "bionnica":
        class BionnicaNet(nn.Module):
            def __init__(self):
                super(BionnicaNet, self).__init__()
                self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1)
                self.conv2 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
                self.fc1 = nn.Linear(128 * 56 * 56, 512)
                self.fc2 = nn.Linear(512, 2)

            def forward(self, x):
                x = torch.relu(self.conv1(x))
                x = torch.relu(self.conv2(x))
                x = x.view(x.size(0), -1)
                x = torch.relu(self.fc1(x))
                x = self.fc2(x)
                return x
        model = BionnicaNet()
    else:
        raise ValueError("Model not supported")

    return model

def calculate_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    return accuracy, sensitivity, specificity

def federated_training_pipeline(models_list, train_data, test_data, transforms=None):
    results = {}
    for model_name in models_list:
        print(f"Training model: {model_name}")
        model = get_model(model_name)
        fl_algorithm = TorchFLAlgorithm(
            model=model,
            optimizer=torch.optim.Adam(model.parameters(), lr=0.001),
            criterion=nn.CrossEntropyLoss(),
        )
        train_node = TrainDataNode(data=train_data, transforms=transforms)
        test_node = TestDataNode(data=test_data, transforms=transforms)
        agg_node = AggregationNode(strategy=FedAvg())
        fl_algorithm.fit(
            train_node=train_node,
            test_node=test_node,
            agg_node=agg_node,
            epochs=5
        )
        y_true = []
        y_pred = []
        for images, labels in test_node:
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            y_true.extend(labels.numpy())
            y_pred.extend(preds.numpy())
        accuracy, sensitivity, specificity = calculate_metrics(y_true, y_pred)
        results[model_name] = {
            "accuracy": accuracy,
            "sensitivity": sensitivity,
            "specificity": specificity
        }

    return results

if __name__ == "__main__":
    images_train = np.random.rand(100, 3, 224, 224)
    labels_train = np.random.randint(0, 2, 100)
    images_test = np.random.rand(30, 3, 224, 224)
    labels_test = np.random.randint(0, 2, 30)

    train_dataset = ColorectalDataset(images_train, labels_train, transform=transforms.ToTensor())
    test_dataset = ColorectalDataset(images_test, labels_test, transform=transforms.ToTensor())
    models_to_train = ["resnet", "alexnet", "zfnet", "bionnica"]
    metrics = federated_training_pipeline(models_to_train, train_dataset, test_dataset)

    for model_name, model_metrics in metrics.items():
        print(f"Metrics for {model_name}:")
        print(f"  Accuracy: {model_metrics['accuracy']:.2f}")
        print(f"  Sensitivity: {model_metrics['sensitivity']:.2f}")
        print(f"  Specificity: {model_metrics['specificity']:.2f}")

import pandas as pd
import os
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from sklearn.model_selection import train_test_split


def load_cervical_cell_data(csv_file, img_dir, target_size=(64, 64)):
    data = pd.read_csv(csv_file)
    images, labels = [], []
    for _, row in data.iterrows():
        img_path = os.path.join(img_dir, row["image_filename"])
        img = load_img(img_path, target_size=target_size)
        images.append(img_to_array(img) / 255.0)
        labels.append(row["label"])
    images = np.array(images)
    labels = np.array(labels)
    x_train, x_test, y_train, y_test = train_test_split(images, labels, test_size=0.2, random_state=42)
    return (x_train, y_train), (x_test, y_test)

(x_train, y_train), (x_test, y_test) = load_cervical_cell_data(
    "cervical.csv", "samples_data"
)

import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

def load_colorectal_polyps_data(image_dir, target_size=(224, 224)):
    datagen = ImageDataGenerator(rescale=1.0/255.0, validation_split=0.2)  # Normalize pixel values

    train_data = datagen.flow_from_directory(
        image_dir,
        target_size=target_size,
        batch_size=32,
        class_mode="binary",
        subset="training"
    )

    val_data = datagen.flow_from_directory(
        image_dir,
        target_size=target_size,
        batch_size=32,
        class_mode="binary",
        subset="validation"
    )

    return train_data, val_data

train_data, val_data = load_colorectal_polyps_data("sample_data/colorectal.csv")

"""SubstraFL, Cervical Cells"""

!pip install substrafl tensorflow scikit-learn numpy pandas

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.optimizers import Adam
from substrafl.nodes import TrainDataNode, TestDataNode, AggregationNode
from substrafl.strategies import FedAvg
from substrafl.algorithms import TensorFlowFLAlgorithm

def load_cervical_cell_data():
    images = np.random.rand(500, 64, 64, 3)
    labels = np.random.randint(0, 2, 500)
    return images, labels

def get_model(model_name, input_shape=(64, 64, 3)):
    if model_name == "resnet":
        base_model = ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
        x = Flatten()(base_model.output)
        x = Dense(128, activation="relu")(x)
        outputs = Dense(2, activation="softmax")(x)
        model = Model(inputs=base_model.input, outputs=outputs)
    elif model_name == "alexnet":
        model = Sequential([
            Conv2D(96, kernel_size=(11, 11), strides=(4, 4), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "zfnet":
        model = Sequential([
            Conv2D(96, kernel_size=(7, 7), strides=(2, 2), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bionnica":
        model = Sequential([
            Conv2D(64, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(128, (3, 3), activation="relu"),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(128, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bfnet":
        model = Sequential([
            Conv2D(32, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            Flatten(),
            Dense(64, activation="relu"),
            Dense(2, activation="softmax")
        ])
    else:
        raise ValueError("Unsupported model name.")

    model.compile(optimizer=Adam(learning_rate=0.001),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model

def calculate_metrics(y_true, y_pred_prob, threshold=0.5):
    y_pred = (y_pred_prob[:, 1] > threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = accuracy_score(y_true, y_pred)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    roc_auc = roc_auc_score(y_true, y_pred_prob[:, 1])
    return accuracy, sensitivity, specificity, roc_auc

def federated_kfold_cross_validation(images, labels, models, k=5):
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    results = []
    for model_name in models:
        print(f"Training {model_name} model across {k} folds...")
        fold_results = []
        for fold, (train_idx, test_idx) in enumerate(skf.split(images, labels)):
            print(f"Fold {fold + 1}/{k} for {model_name}")
            x_train, x_test = images[train_idx], images[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]
            model = get_model(model_name, input_shape=(64, 64, 3))
            train_node = TrainDataNode(data=(x_train, y_train))
            test_node = TestDataNode(data=(x_test, y_test))
            agg_node = AggregationNode(strategy=FedAvg())
            fl_algorithm = TensorFlowFLAlgorithm(model=model)
            fl_algorithm.fit(
                train_node=train_node,
                test_node=test_node,
                agg_node=agg_node,
                epochs=5
            )
            y_pred_prob = model.predict(x_test)
            accuracy, sensitivity, specificity, roc_auc = calculate_metrics(y_test, y_pred_prob)

            fold_results.append({
                "fold": fold + 1,
                "accuracy": accuracy,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "roc_auc": roc_auc
            })
        model_results = pd.DataFrame(fold_results).mean()
        results.append({
            "model": model_name,
            **model_results.to_dict()
        })
    return pd.DataFrame(results)

if __name__ == "__main__":
    images, labels = load_cervical_cell_data()
    models_to_evaluate = ["resnet", "alexnet", "zfnet", "bionnica", "bfnet"]
    results = federated_kfold_cross_validation(images, labels, models=models_to_evaluate, k=5)
    print("Final Cross-Validation Results:")
    print(results)

"""MetisFL, Cervical cells"""

!pip install metisfl tensorflow numpy scikit-learn pandas

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.optimizers import Adam
from metisfl.client.client import Client
from metisfl.server.server import Server
from metisfl.common.dtypes import DatasetSplit

def load_cervical_cell_data():
    images = np.random.rand(500, 64, 64, 3)
    labels = np.random.randint(0, 2, 500)
    return images, labels

def get_model(model_name, input_shape=(64, 64, 3)):
    if model_name == "resnet":
        base_model = ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
        x = Flatten()(base_model.output)
        x = Dense(128, activation="relu")(x)
        outputs = Dense(2, activation="softmax")(x)
        model = Model(inputs=base_model.input, outputs=outputs)
    elif model_name == "alexnet":
        model = Sequential([
            Conv2D(96, kernel_size=(11, 11), strides=(4, 4), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "zfnet":
        model = Sequential([
            Conv2D(96, kernel_size=(7, 7), strides=(2, 2), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bionnica":
        model = Sequential([
            Conv2D(64, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(128, (3, 3), activation="relu"),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(128, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bfnet":
        model = Sequential([
            Conv2D(32, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            Flatten(),
            Dense(64, activation="relu"),
            Dense(2, activation="softmax")
        ])
    else:
        raise ValueError("Unsupported model name.")

    model.compile(optimizer=Adam(learning_rate=0.001),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model

def calculate_metrics(y_true, y_pred_prob, threshold=0.5):
    y_pred = (y_pred_prob[:, 1] > threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = accuracy_score(y_true, y_pred)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    roc_auc = roc_auc_score(y_true, y_pred_prob[:, 1])
    return accuracy, sensitivity, specificity, roc_auc

def federated_kfold_cross_validation(images, labels, models, k=5):
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    results = []
    for model_name in models:
        print(f"Training {model_name} model across {k} folds...")
        fold_results = []
        for fold, (train_idx, test_idx) in enumerate(skf.split(images, labels)):
            print(f"Fold {fold + 1}/{k} for {model_name}")
            x_train, x_test = images[train_idx], images[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]
            model = get_model(model_name, input_shape=(64, 64, 3))

            # Set up MetisFL server and client
            server = Server()
            client = Client(model=model, dataset_split=DatasetSplit(train=(x_train, y_train), test=(x_test, y_test)))
            server.add_client(client)
            server.train(rounds=5)
            y_pred_prob = model.predict(x_test)
            accuracy, sensitivity, specificity, roc_auc = calculate_metrics(y_test, y_pred_prob)

            fold_results.append({
                "fold": fold + 1,
                "accuracy": accuracy,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "roc_auc": roc_auc
            })
        model_results = pd.DataFrame(fold_results).mean()
        results.append({
            "model": model_name,
            **model_results.to_dict()
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    images, labels = load_cervical_cell_data()
    models_to_evaluate = ["resnet", "alexnet", "zfnet", "bionnica", "bfnet"]
    results = federated_kfold_cross_validation(images, labels, models=models_to_evaluate, k=5)
    print("Final Cross-Validation Results:")
    print(results)

"""MetisFL, Colorectal polyps, models: ResNet, AlexNet, ZFNet, Bionnica.

Performance metrics
"""

!pip install metisfl
!pip install numpy pandas scikit-learn tensorflow torchvision

import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix
from metisfl.common.dtypes import DatasetSplit, TrainingStrategy, EvaluationResults
from metisfl.client.client import Client
from metisfl.server.server import Server
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.applications import ResNet50, AlexNet


def load_colorectal_polyps_data():
    train_images = np.random.rand(100, 224, 224, 3)
    train_labels = np.random.randint(0, 2, 100)
    test_images = np.random.rand(30, 224, 224, 3)
    test_labels = np.random.randint(0, 2, 30)
    return train_images, train_labels, test_images, test_labels

def get_model(model_name):
    if model_name == "resnet":
        base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
        x = Flatten()(base_model.output)
        x = Dense(512, activation='relu')(x)
        outputs = Dense(2, activation='softmax')(x)
        model = Model(inputs=base_model.input, outputs=outputs)
    elif model_name == "alexnet":
        model = tf.keras.Sequential([
            Conv2D(96, kernel_size=(11, 11), strides=(4, 4), activation='relu', input_shape=(224, 224, 3)),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation='relu', padding='same'),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation='relu'),
            Dense(4096, activation='relu'),
            Dense(2, activation='softmax')
        ])
    elif model_name == "zfnet":
        model = tf.keras.Sequential([
            Conv2D(96, kernel_size=(7, 7), strides=(2, 2), activation='relu', input_shape=(224, 224, 3)),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation='relu', padding='same'),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation='relu'),
            Dense(4096, activation='relu'),
            Dense(2, activation='softmax')
        ])
    elif model_name == "bionnica":
        model = tf.keras.Sequential([
            Conv2D(64, kernel_size=(3, 3), activation='relu', input_shape=(224, 224, 3)),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(128, kernel_size=(3, 3), activation='relu'),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(512, activation='relu'),
            Dense(2, activation='softmax')
        ])
    else:
        raise ValueError("Unsupported model name")

    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def calculate_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    return accuracy, sensitivity, specificity

def federated_training(models_list, train_data, test_data):
    results = {}
    for model_name in models_list:
        print(f"Training model: {model_name}")
        model = get_model(model_name)
        server = Server(training_strategy=TrainingStrategy.SYNCHRONOUS)
        clients = [Client(model=model, dataset_split=DatasetSplit(train=train_data))]
        server.initialize(clients=clients)
        server.train(rounds=5)
        test_images, test_labels = test_data
        predictions = np.argmax(model.predict(test_images), axis=1)
        accuracy, sensitivity, specificity = calculate_metrics(test_labels, predictions)

        results[model_name] = {
            "accuracy": accuracy,
            "sensitivity": sensitivity,
            "specificity": specificity
        }

    return results

if __name__ == "__main__":
    train_images, train_labels, test_images, test_labels = load_colorectal_polyps_data()
    train_data = (train_images, train_labels)
    test_data = (test_images, test_labels)
    models_to_train = ["resnet", "alexnet", "zfnet", "bionnica"]
    metrics = federated_training(models_to_train, train_data, test_data)
    for model_name, model_metrics in metrics.items():
        print(f"Metrics for {model_name}:")
        print(f"  Accuracy: {model_metrics['accuracy']:.2f}")
        print(f"  Sensitivity: {model_metrics['sensitivity']:.2f}")
        print(f"  Specificity: {model_metrics['specificity']:.2f}")

"""Flower, Cervical cells"""

!pip install flwr tensorflow scikit-learn numpy pandas

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam
import flwr as fl

def load_cervical_cell_data():
    images = np.random.rand(500, 64, 64, 3)
    labels = np.random.randint(0, 2, 500)
    return images, labels

def get_model(model_name, input_shape=(64, 64, 3)):
    if model_name == "resnet":
        base_model = ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
        x = Flatten()(base_model.output)
        x = Dense(128, activation="relu")(x)
        outputs = Dense(2, activation="softmax")(x)
        model = Model(inputs=base_model.input, outputs=outputs)
    elif model_name == "alexnet":
        model = Sequential([
            Conv2D(96, kernel_size=(11, 11), strides=(4, 4), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "zfnet":
        model = Sequential([
            Conv2D(96, kernel_size=(7, 7), strides=(2, 2), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bionnica":
        model = Sequential([
            Conv2D(64, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(128, (3, 3), activation="relu"),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(128, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bfnet":
        model = Sequential([
            Conv2D(32, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            Flatten(),
            Dense(64, activation="relu"),
            Dense(2, activation="softmax")
        ])
    else:
        raise ValueError("Unsupported model name.")

    model.compile(optimizer=Adam(learning_rate=0.001),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model

def calculate_metrics(y_true, y_pred_prob, threshold=0.5):
    y_pred = (y_pred_prob[:, 1] > threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = accuracy_score(y_true, y_pred)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    roc_auc = roc_auc_score(y_true, y_pred_prob[:, 1])
    return accuracy, sensitivity, specificity, roc_auc

class CervicalCellClient(fl.client.NumPyClient):
    def __init__(self, model, train_data, test_data):
        self.model = model
        self.train_images, self.train_labels = train_data
        self.test_images, self.test_labels = test_data

    def get_parameters(self):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        self.model.fit(self.train_images, self.train_labels, epochs=5, batch_size=32, verbose=0)
        return self.model.get_weights(), len(self.train_images), {}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss, accuracy = self.model.evaluate(self.test_images, self.test_labels, verbose=0)
        y_pred_prob = self.model.predict(self.test_images)
        accuracy, sensitivity, specificity, roc_auc = calculate_metrics(self.test_labels, y_pred_prob)
        return loss, len(self.test_images), {"accuracy": accuracy, "sensitivity": sensitivity, "specificity": specificity, "roc_auc": roc_auc}

def federated_kfold_cross_validation(images, labels, models, k=5):
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    results = []
    for model_name in models:
        print(f"Training {model_name} model across {k} folds...")
        fold_results = []
        for fold, (train_idx, test_idx) in enumerate(skf.split(images, labels)):
            print(f"Fold {fold + 1}/{k} for {model_name}")
            x_train, x_test = images[train_idx], images[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]

            model = get_model(model_name, input_shape=(64, 64, 3))

            client = CervicalCellClient(model, train_data=(x_train, y_train), test_data=(x_test, y_test))
            fl.client.start_numpy_client(server_address="localhost:8080", client=client)

            y_pred_prob = model.predict(x_test)
            accuracy, sensitivity, specificity, roc_auc = calculate_metrics(y_test, y_pred_prob)

            fold_results.append({
                "fold": fold + 1,
                "accuracy": accuracy,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "roc_auc": roc_auc
            })
        model_results = pd.DataFrame(fold_results).mean()
        results.append({
            "model": model_name,
            **model_results.to_dict()
        })

    return pd.DataFrame(results)

if __name__ == "__main__":
    images, labels = load_cervical_cell_data()
    models_to_evaluate = ["resnet", "alexnet", "zfnet", "bionnica", "bfnet"]
    results = federated_kfold_cross_validation(images, labels, models=models_to_evaluate, k=5)
    print("Final Cross-Validation Results:")
    print(results)

"""
Flower, Colorectal polyps, models: ResNet, AlexNet, ZFNet, Bionnica.

Performance metrics


"""

!pip install flwr tensorflow scikit-learn numpy

import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix
from flwr.server import start_server
from flwr.client import start_client, NumPyClient
from flwr.common import ndarrays_to_parameters
from typing import Tuple

def load_colorectal_polyps_data():
    train_images = np.random.rand(100, 224, 224, 3)
    train_labels = np.random.randint(0, 2, 100)
    test_images = np.random.rand(30, 224, 224, 3)
    test_labels = np.random.randint(0, 2, 30)
    return train_images, train_labels, test_images, test_labels

def create_model():
    base_model = tf.keras.applications.ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
    x = tf.keras.layers.Flatten()(base_model.output)
    x = tf.keras.layers.Dense(512, activation="relu")(x)
    outputs = tf.keras.layers.Dense(2, activation="softmax")(x)
    model = tf.keras.Model(inputs=base_model.input, outputs=outputs)
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model

class ColorectalClient(NumPyClient):
    def __init__(self, model, train_data, test_data):
        self.model = model
        self.train_images, self.train_labels = train_data
        self.test_images, self.test_labels = test_data

    def get_parameters(self):
        return ndarrays_to_parameters(self.model.get_weights())

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        self.model.fit(self.train_images, self.train_labels, epochs=1, batch_size=32, verbose=0)
        return self.get_parameters(), len(self.train_images), {}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss, accuracy = self.model.evaluate(self.test_images, self.test_labels, verbose=0)
        predictions = np.argmax(self.model.predict(self.test_images), axis=1)
        accuracy, sensitivity, specificity = calculate_metrics(self.test_labels, predictions)
        return loss, len(self.test_images), {"accuracy": accuracy, "sensitivity": sensitivity, "specificity": specificity}

def calculate_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    return accuracy, sensitivity, specificity

def start_flower_server():
    start_server(config={"num_rounds": 5})

def start_flower_client(train_data, test_data):
    model = create_model()
    client = ColorectalClient(model, train_data, test_data)
    start_client(client)

if __name__ == "__main__":
    train_images, train_labels, test_images, test_labels = load_colorectal_polyps_data()
    train_data = (train_images, train_labels)
    test_data = (test_images, test_labels)

    # Start the Flower server and clients
    import multiprocessing
    server_process = multiprocessing.Process(target=start_flower_server)
    client_process = multiprocessing.Process(target=start_flower_client, args=(train_data, test_data))

    server_process.start()
    client_process.start()

    server_process.join()
    client_process.join()

"""Fed-Biomed, Cervical cells"""

!pip install numpy pandas scikit-learn tensorflow

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.optimizers import Adam
from fedbiomed.researcher.environments.environments import FedBioMedResearcherEnv
from fedbiomed.common.constants import TrainingApproaches
from fedbiomed.researcher.model_manager import TensorFlowModelManager
from fedbiomed.common.messaging import ModelTrainingArgs


def load_cervical_cell_data():
    images = np.random.rand(500, 64, 64, 3)
    labels = np.random.randint(0, 2, 500)
    return images, labels

def get_model(model_name, input_shape=(64, 64, 3)):
    if model_name == "resnet":
        base_model = ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
        x = Flatten()(base_model.output)
        x = Dense(128, activation="relu")(x)
        outputs = Dense(2, activation="softmax")(x)
        model = Model(inputs=base_model.input, outputs=outputs)
    elif model_name == "alexnet":
        model = Sequential([
            Conv2D(96, kernel_size=(11, 11), strides=(4, 4), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "zfnet":
        model = Sequential([
            Conv2D(96, kernel_size=(7, 7), strides=(2, 2), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Conv2D(256, kernel_size=(5, 5), activation="relu", padding="same"),
            MaxPooling2D(pool_size=(3, 3), strides=(2, 2)),
            Flatten(),
            Dense(4096, activation="relu"),
            Dense(4096, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bionnica":
        model = Sequential([
            Conv2D(64, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(128, (3, 3), activation="relu"),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(128, activation="relu"),
            Dense(2, activation="softmax")
        ])
    elif model_name == "bfnet":
        model = Sequential([
            Conv2D(32, (3, 3), activation="relu", input_shape=input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            Flatten(),
            Dense(64, activation="relu"),
            Dense(2, activation="softmax")
        ])
    else:
        raise ValueError(f"Model {model_name} is not supported.")

    model.compile(optimizer=Adam(learning_rate=0.001),
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model

def calculate_metrics(y_true, y_pred_prob, threshold=0.5):
    y_pred = (y_pred_prob[:, 1] > threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = accuracy_score(y_true, y_pred)
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    roc_auc = roc_auc_score(y_true, y_pred_prob[:, 1])
    return accuracy, sensitivity, specificity, roc_auc

def federated_kfold_cross_validation(images, labels, models, k=5):
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    results = []

    for model_name in models:
        print(f"Training {model_name} model across {k} folds...")
        fold_results = []

        for fold, (train_idx, test_idx) in enumerate(skf.split(images, labels)):
            print(f"Fold {fold + 1}/{k} for {model_name}")

            x_train, x_test = images[train_idx], images[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]

            model = get_model(model_name, input_shape=(64, 64, 3))

            # Fed-BioMed environment setup
            env = FedBioMedResearcherEnv()
            model_manager = TensorFlowModelManager(
                model=model,
                training_approach=TrainingApproaches.SGD,
                dataset_split={"train": (x_train, y_train), "test": (x_test, y_test)}
            )

            training_args = ModelTrainingArgs(
                rounds=5,
                batch_size=32,
                epochs=5
            )
            env.start_training(model_manager, training_args)
            y_pred_prob = model.predict(x_test)
            accuracy, sensitivity, specificity, roc_auc = calculate_metrics(y_test, y_pred_prob)
            fold_results.append({
                "fold": fold + 1,
                "accuracy": accuracy,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "roc_auc": roc_auc
            })
        model_results = pd.DataFrame(fold_results).mean()
        results.append({
            "model": model_name,
            **model_results.to_dict()
        })
    return pd.DataFrame(results)

if __name__ == "__main__":
    images, labels = load_cervical_cell_data()
    models_to_evaluate = ["resnet", "alexnet", "zfnet", "bionnica", "bfnet"]
    results = federated_kfold_cross_validation(images, labels, models=models_to_evaluate, k=5)
    print("Final Cross-Validation Results:")
    print(results)

"""
Fed-Biomed, Colorectal polyps, models: ResNet, AlexNet, ZFNet, Bionnica.

Performance metrics
"""

!pip install scikit-learn tensorflow numpy

import numpy as np
import tensorflow as tf
from sklearn.metrics import confusion_matrix
from fedbiomed.researcher.environments.environments import FedBioMedResearcherEnv
from fedbiomed.common.constants import ResearcherRequestStatus
from fedbiomed.common.message_types import Messages
from fedbiomed.researcher.requests.model_request import ModelRequest


env = FedBioMedResearcherEnv()

def load_colorectal_polyps_data():
    train_images = np.random.rand(100, 224, 224, 3)
    train_labels = np.random.randint(0, 2, 100)
    test_images = np.random.rand(30, 224, 224, 3)
    test_labels = np.random.randint(0, 2, 30)
    return train_images, train_labels, test_images, test_labels

def create_model():
    base_model = tf.keras.applications.ResNet50(weights="imagenet", include_top=False, input_shape=(224, 224, 3))
    x = tf.keras.layers.Flatten()(base_model.output)
    x = tf.keras.layers.Dense(512, activation="relu")(x)
    outputs = tf.keras.layers.Dense(2, activation="softmax")(x)
    model = tf.keras.Model(inputs=base_model.input, outputs=outputs)
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model

def calculate_metrics(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    return accuracy, sensitivity, specificity

def federated_training(env, train_images, train_labels, test_images, test_labels):
    model = create_model()
    model_request = ModelRequest(
        model=model,
        train_data=(train_images, train_labels),
        test_data=(test_images, test_labels),
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    result = env.run(model_request)

    if result.status == ResearcherRequestStatus.SUCCESS:
        predictions = np.argmax(model.predict(test_images), axis=1)
        accuracy, sensitivity, specificity = calculate_metrics(test_labels, predictions)
        return {"accuracy": accuracy, "sensitivity": sensitivity, "specificity": specificity}
    else:
        print("Training failed!")
        return None

if __name__ == "__main__":
    train_images, train_labels, test_images, test_labels = load_colorectal_polyps_data()

    metrics = federated_training(env, train_images, train_labels, test_images, test_labels)

    if metrics:
        print(f"Accuracy: {metrics['accuracy']:.2f}")
        print(f"Sensitivity: {metrics['sensitivity']:.2f}")
        print(f"Specificity: {metrics['specificity']:.2f}")

