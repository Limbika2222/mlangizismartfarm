import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models
import os

# === Verify TensorFlow version ===
print(f"✅ TensorFlow version: {tf.__version__}")

# === Define dataset paths ===
train_dir = 'maize_dataset/train'
test_dir = 'maize_dataset/test'

# === Check if dataset paths exist ===
if not os.path.exists(train_dir) or not os.path.exists(test_dir):
    print("❌ Dataset folders not found. Please check your dataset path.")
    exit()

# === Image data generators ===
train_datagen = ImageDataGenerator(rescale=1./255)
test_datagen = ImageDataGenerator(rescale=1./255)

# === Load dataset ===
print("🔄 Loading training data...")
train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(150, 150),
    batch_size=32,
    class_mode='categorical'
)

print("🔄 Loading testing data...")
test_generator = test_datagen.flow_from_directory(
    test_dir,
    target_size=(150, 150),
    batch_size=32,
    class_mode='categorical'
)

# === Define the CNN model ===
print("🛠️ Building CNN model...")
model = models.Sequential([
    layers.Conv2D(32, (3,3), activation='relu', input_shape=(150, 150, 3)),
    layers.MaxPooling2D((2,2)),
    
    layers.Conv2D(64, (3,3), activation='relu'),
    layers.MaxPooling2D((2,2)),
    
    layers.Conv2D(128, (3,3), activation='relu'),
    layers.MaxPooling2D((2,2)),
    
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dense(train_generator.num_classes, activation='softmax')
])

# === Compile the model ===
print("⚙️ Compiling model...")
model.compile(optimizer='adam',
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# === Train the model ===
print("🚀 Starting training...")
history = model.fit(
    train_generator,
    steps_per_epoch=train_generator.samples // train_generator.batch_size,
    epochs=10,
    validation_data=test_generator,
    validation_steps=test_generator.samples // test_generator.batch_size
)

# === Save the model ===
model.save('maize_disease_model.h5')
print("✅ Model training completed and saved as maize_disease_model.h5")
