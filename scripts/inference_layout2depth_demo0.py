from diffusers import UniPCMultistepScheduler
from threeDIS.utils import seed_everything, load_migc
from threeDIS.pipeline_stable_diffusion_layout2depth import StableDiffusionL2DPipeline, MIGCProcessor
import os
import torch
from PIL import Image
from copy import deepcopy
import numpy as np


if __name__ == '__main__':
    # Construct Layout-to-Depth pipeline
    sd_path = "Intel/ldm3d-4c" if not os.path.isdir('/mnt/sda/zdw/ckpt/ldm3d-4c') else '/mnt/sda/zdw/ckpt/ldm3d-4c'
    pipe = StableDiffusionL2DPipeline.from_pretrained(sd_path)
    
    # load fine-tuned Text-to-Depth model
    unet_path = './pretrained_weights/unet_0901.ckpt'
    assert os.path.isfile(unet_path), f"Checkpoint file not found at {unet_path}"
    pipe.unet.load_state_dict(torch.load(unet_path))

    # load Layout-to-Depth Adapter
    layout_adapter_ckpt_path = './pretrained_weights/layout_adapter.ckpt'
    assert os.path.isfile(layout_adapter_ckpt_path), f"Checkpoint file not found at {layout_adapter_ckpt_path}"
    load_migc(pipe.unet, layout_adapter_ckpt_path, attn_processor=MIGCProcessor)
    
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)

    pipe = pipe.to("cuda")


    seed = 11279306965410786290
    seed_everything(seed)
    

    img_prompt = "4k, best quality, masterpiece, ultra high res, ultra detailed, a beautiful woman is reading a book."
    instance_prompts = [["a beautiful woman", 'a book', 'a table', 'a lamp', 'long hair', 'a bed', 'legs']]
    for instance_prompt in instance_prompts[0]:
        img_prompt += ',' + instance_prompt
    prompt_final = [[img_prompt]]
    for instance_prompt in instance_prompts[0]:
        prompt_final[0].append(instance_prompt)

    bboxes = [[[ 0.296875, 0.046875, 0.6875, 0.9375], [0.34375, 0.34375, 0.625, 0.515625], [0.765625, 0.296875, 1, 0.84375], 
               [0.78125, 0.03125, 1, 0.453125], [0.359375, 0.046875, 0.609375, 0.28125], [0.046875, 0.015625, 0.734375, 0.984375],
               [0.34375, 0.5, 0.65625, 0.984375]]]

    image = pipe(deepcopy(prompt_final), bboxes, num_inference_steps=30, guidance_scale=6.5, 
                                    MIGCsteps=15, NaiveFuserSteps=30, aug_phase_with_and=False,
                                    negative_prompt='worst quality, low quality, bad anatomy, worst quality, low quality, bad anatomy, watermark, text, blurry, extra hands').images[0]
    
    image_np = np.array(image)
    
    from PIL import Image
    image_rgb = Image.fromarray((image_np[..., 0: 3]).astype('uint8'))
    image = Image.fromarray((image_np[..., 3]).astype('uint8'))
    image.save("girl_depth.png")
    