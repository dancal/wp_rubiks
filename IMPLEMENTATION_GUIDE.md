"""
루빅스 큐브 색상 감지 개선 가이드

파일: main.py
변경 사항:
1. import 추가 (라인 30 후)
2. readcube_thread 메서드 개선 (라인 992-1206)
3. get_processed_image 메서드 개선 (라인 693-705)
"""

# ============================================================================
# [STEP 1] main.py 라인 30 (from scipy.spatial import distance) 뒤에 추가:
# ============================================================================

from color_detector import (
    ColorCalibrator, ColorMatcher, ImageProcessor,
    StabilityChecker, get_color_name
)


# ============================================================================
# [STEP 2] get_processed_image 메서드 개선 (라인 693-705)
# ============================================================================

def get_processed_image(self):
    """
    Captures an image and processes it with IMPROVED filtering.
    Applies bilateral filtering and CLAHE for better color detection.
    :return: RGB image as numpy array.
    """
    from color_detector import ImageProcessor
    
    sleep(0.3)
    img = self.capture()
    img = np.asarray(img)
    
    # ✅ 개선: 이미지 전처리 적용
    img_processor = ImageProcessor()
    img = img_processor.preprocess_image(
        img,
        apply_clahe=logger.getEffectiveLevel() == logging.DEBUG,  # 디버그 모드에서만
        apply_bilateral=True
    )
    
    return img


# ============================================================================
# [STEP 3] readcube_thread 메서드 완전 대체 (라인 992-1206)
# ============================================================================

def readcube_thread(self):
    """
    Method which scans the cube's surface with IMPROVED color detection.
    Uses dynamic calibration, LAB color space, and stability checking.
    :return: Nothing.
    """
    logger.debug('reading cube')
    self.pub.publish(self.channel, {
        'fix_button_locked': self.__buttons_status(True),
        'release_button_locked': self.__buttons_status(True),
        'infinite_button_locked': self.__buttons_status(True),
        'read_button_locked': self.__buttons_status(True),
        'solve_button_locked': self.__buttons_status(True),
        'scramble_button_locked': self.__buttons_status(True),
        'read_status': 0,
        'solve_status': 0,
        'scramble_status': 0
    })

    # ✅ Initialize improved color detection
    calibrator = ColorCalibrator()
    matcher = ColorMatcher()
    img_processor = ImageProcessor()
    stability_checker = StabilityChecker(
        num_samples=self.config.get('camera', {}).get('num_stability_samples', 3)
    )

    # Instantiate arms and scan cube
    robot_arms = self.__instantiate_arms_in_release_mode(self.config)
    generator = arms.ArmSolutionGenerator(*robot_arms)
    if not self.isFixedCube:
        generator.reposition_arms(delay=0.5)
        generator.fix()

    # Generate motion sequence for scanning all 6 faces
    # F
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_towards_right()

    # L
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_towards_right()

    # B
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_towards_right()

    # R
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_towards_right()
    generator.rotate_cube_upwards()

    # U
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_upwards()
    generator.rotate_cube_upwards()

    # D
    generator.take_capture_order()
    generator.append_command('take photo')
    generator.take_capture_reset()
    generator.rotate_cube_upwards()

    # Save generator and execute sequence
    self.generator = generator
    sequence = generator.arms_solution
    numeric_faces = []
    length = len(sequence)
    pic_counter = 0

    # Execute motion sequence and capture photos
    for idx, step in enumerate(sequence):
        if self.thread_stopper.is_set():
            return
        if step:
            logger.debug('Execute \'' + str(step) + '\'')
            if step == 'take photo':
                xoff = self.config['camera']['X Offset (px)']
                yoff = self.config['camera']['Y Offset (px)']
                dim = self.config['camera']['Size (px)']
                pad = self.config['camera']['Pad (px)']

                camera.cv_images.append(camera.get_overlayed_processed_image(xoff, yoff, dim, pad))
                lab_face = camera.get_camera_color_patches(xoff, yoff, dim, pad, pic_counter)
                numeric_faces.append(lab_face)
                pic_counter += 1
            else:
                success = self.__execute_command(step)

        self.pub.publish(self.channel, {
            'fix_button_locked': self.__buttons_status(True),
            'release_button_locked': self.__buttons_status(True),
            'infinite_button_locked': self.__buttons_status(True),
            'read_button_locked': self.__buttons_status(True),
            'solve_button_locked': self.__buttons_status(True),
            'scramble_button_locked': self.__buttons_status(True),
            'read_status': 100 * (idx + 1) / length,
            'solve_status': 0,
            'scramble_status': 0
        })

    # ============================================================================
    # ✅ IMPROVED COLOR DETECTION SECTION
    # ============================================================================
    logger.info("\n" + "=" * 70)
    logger.info("🔵 IMPROVED RUBIK'S CUBE COLOR DETECTION STARTED")
    logger.info("=" * 70)

    # Reorient faces to URFDLB order
    reoriented_faces = [
        numeric_faces[5],
        numeric_faces[1],
        numeric_faces[0],
        numeric_faces[4],
        numeric_faces[3],
        numeric_faces[2]
    ]

    # Reshape faces to (9, 3) for color processing
    for i in range(6):
        reoriented_faces[i] = reoriented_faces[i].reshape((3*3, 3))

    # ✅ Step 1: Dynamic Color Calibration
    logger.info("\n📍 [Step 1/4] Dynamic Color Calibration from Face Centers")
    logger.info("-" * 70)
    
    if calibrator.calibrate_from_centers(reoriented_faces):
        reference_colors_rgb = calibrator.reference_colors_rgb
        logger.info("✅ Calibration SUCCESSFUL")
        logger.info("   Reference colors extracted from center stickers:")
        for color_idx, color_rgb in enumerate(reference_colors_rgb):
            color_name = get_color_name(color_idx)
            logger.info(f"      {color_idx}: {color_name:8s} = RGB{tuple(color_rgb)}")
    else:
        logger.warning("⚠️  Calibration FAILED - Using default REFERENCE_COLORS")
        reference_colors_rgb = np.array(REFERENCE_COLORS, dtype=np.uint8)
        for color_idx, color_rgb in enumerate(reference_colors_rgb):
            logger.info(f"      {color_idx}: {get_color_name(color_idx):8s} = RGB{tuple(color_rgb)}")

    # ✅ Step 2: Match Sticker Colors to References
    logger.info("\n🎨 [Step 2/4] Matching 9 Stickers to 6 Reference Colors")
    logger.info("-" * 70)
    
    all_matched_indices = []
    all_matched_labels = []
    face_names = ['U', 'R', 'F', 'D', 'L', 'B']

    for face_idx, face_colors in enumerate(reoriented_faces):
        face_rgb = (face_colors * 255).astype(np.uint8)

        # Match colors using LAB distance
        matched_indices = matcher.match_sticker_colors(face_rgb, reference_colors_rgb)

        # Improve consistency by averaging same-color stickers
        corrected_colors = matcher.improve_color_consistency(face_rgb, matched_indices)

        # Check stability
        stability = stability_checker.check_stability(corrected_colors)
        stability_threshold = self.config.get('camera', {}).get('stability_threshold', 0.7)

        all_matched_indices.append(matched_indices)
        all_matched_labels.extend(matched_indices.flatten().tolist())

        face_name = face_names[face_idx]
        stability_icon = "✅" if stability >= stability_threshold else "⚠️"
        logger.info(f"   Face {face_name}: stability={stability:.3f} {stability_icon}")

    rubiks_labels = np.array(all_matched_labels, dtype=int)

    # ✅ Step 3: Validate Color Distribution
    logger.info("\n🔍 [Step 3/4] Validating Color Distribution")
    logger.info("-" * 70)
    
    labels_count = dict(Counter(rubiks_labels))
    logger.info(f"   Total colors detected: {len(labels_count)}")
    logger.info(f"   Distribution: {labels_count}")

    is_valid = len(labels_count) == 6 and all(count == 9 for count in labels_count.values())

    if is_valid:
        logger.info("✅ PERFECT COLOR DISTRIBUTION: 6 colors × 9 stickers each")
        for color_idx in range(6):
            count = labels_count.get(color_idx, 0)
            color_name = get_color_name(color_idx)
            logger.info(f"      {color_name:8s}: {count} stickers")
    else:
        logger.error("❌ INVALID COLOR DISTRIBUTION DETECTED")
        logger.error(f"   Expected: 6 different colors, 9 stickers per color")
        logger.error(f"   Got: {len(labels_count)} colors with distribution {labels_count}")
        logger.error("\n   Detailed per-face breakdown:")
        for face_idx, indices in enumerate(all_matched_indices):
            face_counts = dict(Counter(indices.flatten()))
            logger.error(f"      Face {face_names[face_idx]}: {face_counts}")

    # ✅ Step 4: Generate Solution
    logger.info("\n⚙️  [Step 4/4] Generating Rubik's Cube Solution")
    logger.info("-" * 70)

    if is_valid:
        try:
            cube_centers = list(range(6))
            self.cubesolution = self.__generate_handwritten_solution_from_cube_state(
                cube_centers, rubiks_labels
            )
            logger.info("✅ Solution GENERATED Successfully")
            logger.info(f"   Moves: {' '.join(self.cubesolution)}")
            logger.info(f"   Total moves: {len(self.cubesolution)}")
        except Exception as e:
            logger.error(f"❌ Failed to generate solution: {e}")
            self.cubesolution = None
    else:
        logger.error("❌ Solution generation SKIPPED due to invalid color distribution")
        self.cubesolution = None

    logger.info("=" * 70)
    logger.info("🔵 COLOR DETECTION PROCESS COMPLETED\n")

    # Mark thread as finished
    self.thread_stopper.set()

    # Handle already-solved cube
    if self.cubesolution == []:
        self.stop(hard=False)

    # Publish completion status
    self.pub.publish(self.channel, {
        'fix_button_locked': self.__buttons_status(False),
        'release_button_locked': self.__buttons_status(False),
        'infinite_button_locked': self.__buttons_status(False),
        'read_button_locked': self.__buttons_status(False),
        'solve_button_locked': self.__buttons_status(False),
        'scramble_button_locked': self.__buttons_status(False),
        'read_status': 100,
        'solve_status': 0,
        'scramble_status': 0
    })
